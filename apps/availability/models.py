from django.db import models
from apps.experiences.models import Experience


class ExperienceAvailability(models.Model):
    """
    Reglas por experiencia:
    - weekdays: lista de ints [0..6] donde 0=Lunes, 6=Domingo
    - start_date / end_date: rango opcional
    - daily_capacity_people: capacidad total de personas por día (opcional)
    """
    experience = models.OneToOneField(
        Experience,
        on_delete=models.CASCADE,
        related_name="availability",
    )

    weekdays = models.JSONField(default=list, blank=True)  # ejemplo: [0,1,2,3,4]
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)

    daily_capacity_people = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Capacidad total de personas por día (vacío = sin límite).",
    )

    daily_capacity_bookings = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Máximo de excursiones (reservas aceptadas) por día. Vacío = sin límite.",
    )

    max_people_per_booking = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Máximo de personas por excursión (reserva). Vacío = sin límite.",
    )

    is_enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Availability({self.experience.title})"


class AvailabilityBlock(models.Model):
    availability = models.ForeignKey(
        ExperienceAvailability,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("availability", "date")
        ordering = ["date"]

    def __str__(self):
        return f"Block({self.availability.experience.title} - {self.date})"
