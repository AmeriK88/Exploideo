from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager


class InvoiceSequence(models.Model):
    """
    Lleva el contador correlativo por año.
    Ej: año 2026 -> last_number = 123  => siguiente será 124
    """
    year = models.PositiveIntegerField(unique=True)
    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.year}: {self.last_number}"


class Invoice(models.Model):
    if TYPE_CHECKING:
        items: "RelatedManager[InvoiceItem]"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ISSUED = "issued", "Issued"
        VOID = "void", "Void"

        # tipo de factura (normal o rectificativa)
    class Kind(models.TextChoices):
        STANDARD = "standard", "Standard"
        RECTIFICATIVE = "rectificative", "Rectificative"

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.STANDARD,
        db_index=True,
    )

    # si es rectificativa, referencia a la factura original
    rectifies = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rectifications",
        help_text="Factura original que esta factura rectifica (abono/rectificación).",
    )

    rectification_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Motivo de rectificación (cancelación, cambio de fecha, etc.)",
    )

    # Identificación
    number = models.CharField(max_length=20, unique=True, blank=True)  # "2026-000001"
    year = models.PositiveIntegerField(db_index=True, blank=True, null=True)
    seq = models.PositiveIntegerField(db_index=True, blank=True, null=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)

    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="invoice",
        null=True,
        blank=True,
        help_text="Reserva asociada a esta factura (si aplica).",
    )

    # Relación (de momento: quien recibe la factura)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    # Datos “snapshot” (importante para legal / histórico)
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField()

    # Importes (guardados, no calculados “al vuelo”)
    currency = models.CharField(max_length=3, default="EUR")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["year", "seq"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="standard", rectifies__isnull=True) |
                    Q(kind="rectificative", rectifies__isnull=False)
                ),
                name="invoice_kind_rectifies_consistency",
            )
        ]

    def __str__(self):
        return self.number or f"Invoice(draft:{self.pk})"

    @staticmethod
    def _next_number():
        """
        Genera correlativo por año de forma segura con lock (select_for_update).
        """
        now = timezone.localtime(timezone.now())
        year = now.year

        with transaction.atomic():
            seq_obj, _ = InvoiceSequence.objects.select_for_update().get_or_create(year=year)
            seq_obj.last_number += 1
            seq_obj.save(update_fields=["last_number"])
            seq = seq_obj.last_number

        number = f"{year}-{seq:06d}"
        return year, seq, number

    def recalc_totals(self, save=True):
        items = list(self.items.all())

        subtotal = sum((i.line_subtotal for i in items), Decimal("0.00"))
        tax_total = sum((i.tax_amount for i in items), Decimal("0.00"))
        total = subtotal + tax_total

        self.subtotal = subtotal
        self.tax_total = tax_total
        self.total = total

        if save:
            self.save(update_fields=["subtotal", "tax_total", "total"])

    def issue(self):
        if self.status != self.Status.DRAFT:
            return

        with transaction.atomic():
            # bloquea la fila
            inv = Invoice.objects.select_for_update().get(pk=self.pk)
            if inv.status != Invoice.Status.DRAFT:
                return

            if not inv.number:
                year, seq, number = inv._next_number()
                inv.year = year
                inv.seq = seq
                inv.number = number

            inv.recalc_totals(save=False)
            inv.status = Invoice.Status.ISSUED
            inv.issued_at = timezone.now()
            inv.save(update_fields=[
                "year", "seq", "number",
                "subtotal", "tax_total", "total",
                "status", "issued_at"
            ])

            # refleja cambios en self por si sigues usando el objeto
            self.refresh_from_db()



class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="items", on_delete=models.CASCADE)

    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # IVA (por línea) — simple y escalable
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal("0.00"),
        help_text="IVA en porcentaje. Ej: 7.00, 21.00"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} x{self.quantity}"

    @property
    def line_subtotal(self):
        return (self.unit_price * Decimal(self.quantity)).quantize(Decimal("0.01"))

    @property
    def tax_amount(self):
        return (self.line_subtotal * (self.tax_rate / Decimal("100"))).quantize(Decimal("0.01"))

    @property
    def line_total(self):
        return (self.line_subtotal + self.tax_amount).quantize(Decimal("0.01"))
