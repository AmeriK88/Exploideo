from __future__ import annotations

from decimal import Decimal
from django.db import transaction

from apps.billing.models import Invoice, InvoiceItem


def create_rectificative_for_invoice(
    original: Invoice,
    *,
    reason: str = "Cancelación dentro de política",
) -> Invoice:
    """
    Crea una factura rectificativa que anula el 100% de la original.
    - Idempotente: si ya existe, la devuelve.
    - Segura: lock sobre la original.
    """

    if original.status != Invoice.Status.ISSUED:
        raise ValueError("Solo se puede rectificar una factura ISSUED.")

    if original.kind == Invoice.Kind.RECTIFICATIVE:
        raise ValueError("No se puede rectificar una rectificativa.")

    with transaction.atomic():
        original = Invoice.objects.select_for_update().get(pk=original.pk)

        # Idempotencia real: si ya hay rectificativa, devolverla
        existing = original.rectifications.filter(kind=Invoice.Kind.RECTIFICATIVE).first() 
        if existing:
            return existing

        rect = Invoice.objects.create(
            kind=Invoice.Kind.RECTIFICATIVE,
            rectifies=original,
            rectification_reason=reason,

            booking=None,

            customer=original.customer,
            customer_name=original.customer_name,
            customer_email=original.customer_email,
            currency=original.currency,
        )

        # Líneas en negativo
        for it in original.items.all():
            InvoiceItem.objects.create(
                invoice=rect,
                description=f"RECTIFICA: {it.description}",
                quantity=it.quantity,
                unit_price=(Decimal("0.00") - it.unit_price),
                tax_rate=it.tax_rate,
            )

        rect.issue()
        return rect