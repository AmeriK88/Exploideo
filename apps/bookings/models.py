from __future__ import annotations
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from apps.experiences.models import Experience
from apps.bookings.services import validate_minors_policy

if TYPE_CHECKING:
    from apps.billing.models import Invoice


class Booking(models.Model):
    if TYPE_CHECKING:
        invoice: "Invoice"

    # ------------------------------------------------------------
    # Idioma preferido (SINGLE SOURCE OF TRUTH) -> core.Language
    # Ya NO legacy: obligatorio para nuevas reservas.
    # ------------------------------------------------------------
    preferred_language = models.ForeignKey(
        "core.Language",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    class TransportMode(models.TextChoices):
        OWN_VEHICLE = "own_vehicle", "Vehículo propio"
        BICYCLE = "bicycle", "Bicicleta"
        ON_FOOT = "on_foot", "A pie"
        MINIBUS = "minibus", "Minibus"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        CANCELED = "canceled", "Canceled"
        CHANGE_REQUESTED = "change_requested", "Change requested"
        CANCEL_REQUESTED = "cancel_requested", "Cancel requested"

    experience = models.ForeignKey(
        Experience,
        on_delete=models.CASCADE,
        related_name="bookings",
    )

    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        limit_choices_to={"role": "traveler"},
    )

    date = models.DateField()

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0, help_text="Niños 2-11 (50%)")
    infants = models.PositiveIntegerField(default=0, help_text="Bebés 0-1 (gratis)")

    # Agregado coherente
    people = models.PositiveIntegerField(default=1, editable=False)

    transport_mode = models.CharField(
        max_length=20,
        choices=TransportMode.choices,
        default=TransportMode.OWN_VEHICLE,
    )

    pickup_notes = models.CharField(max_length=255, blank=True)

    unit_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    seen_by_traveler = models.BooleanField(default=True)
    seen_by_guide = models.BooleanField(default=True)

    notes = models.TextField(blank=True)
    guide_response = models.TextField(blank=True)

    extras = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    pickup_time = models.TimeField(null=True, blank=True)
    meeting_point = models.CharField(max_length=255, blank=True)

    @property
    def total_people(self) -> int:
        return (self.adults or 0) + (self.children or 0) + (self.infants or 0)

    @property
    def change_blocked_reason(self):
        if self.status != Booking.Status.CHANGE_REQUESTED:
            return None

        change = (self.extras or {}).get("change_request") or {}

        adults = change.get("adults", self.adults) or 0
        children = change.get("children", self.children) or 0
        infants = change.get("infants", self.infants) or 0

        # Aquí ya existe booking, así que es correcto usar self.experience
        try:
            validate_minors_policy(self.experience, adults, children, infants)
        except ValidationError as e:
            return str(e)

        return None

    def clean(self):
        super().clean()

        # ✅ Evitar RelatedObjectDoesNotExist durante form.is_valid()
        exp_id = getattr(self, "experience_id", None)
        lang_id = getattr(self, "preferred_language_id", None)

        if not exp_id or not lang_id:
            return

        # Si quieres ir ultra-seguro, evita cargar self.experience:
        # exp = Experience.objects.select_related("guide").filter(pk=exp_id).first()
        # pero en tu caso, como ya estás guardando FK real, usar self.experience suele ir bien.
        guide_profile = getattr(self.experience.guide, "guide_profile", None)
        if not guide_profile:
            raise ValidationError({"preferred_language": "El guía no tiene perfil configurado."})

        allowed_ids = set(guide_profile.languages.values_list("id", flat=True))
        if lang_id not in allowed_ids:
            raise ValidationError({"preferred_language": "Ese idioma no está disponible para este guía."})

    def save(self, *args, **kwargs):
        self.people = self.total_people
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        exp_id = getattr(self, "experience_id", None)
        exp_title = self.experience.title if exp_id else "—"
        traveler_name = getattr(self.traveler, "username", "—")
        return f"Booking({exp_title}) - {traveler_name} - {self.status}"