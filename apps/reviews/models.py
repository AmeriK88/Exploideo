from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

from apps.experiences.models import Experience
from apps.bookings.models import Booking


class Review(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PUBLISHED = "published", "Published"
        FLAGGED = "flagged", "Flagged"

    experience = models.ForeignKey(
        Experience,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    traveler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    # Contexto real (fecha/idioma/guía/etc. desde Booking)
    booking = models.ForeignKey(
        Booking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        help_text="Reserva asociada (para contexto: fecha, idioma, guía, etc.)",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)

    # Moderación
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    flagged_reason = models.CharField(max_length=255, blank=True)

    # Respuesta pública del guía
    guide_reply = models.TextField(blank=True)
    guide_replied_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("experience", "traveler") 
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Review({self.experience.title}) - {self.traveler.username} - {self.rating}"

    # Auto-moderation simple basado en palabras clave
    SPAM_WORDS = {"viagra", "casino", "crypto", "bitcoin", "xxx", "onlyfans", "telegram"}
    TOXIC_WORDS = {"idiota", "estafa", "mierda", "cabron", "gilipollas"}

    def _auto_moderate(self):
        text = (self.comment or "").lower()

        if any(w in text for w in self.SPAM_WORDS):
            return self.Status.FLAGGED, "Posible spam"

        if any(w in text for w in self.TOXIC_WORDS):
            return self.Status.FLAGGED, "Lenguaje ofensivo"

        return self.Status.PUBLISHED, ""

    def save(self, *args, **kwargs):
        # Si es creación (no existe aún)
        if not self.pk:
            status, reason = self._auto_moderate()
            self.status = status
            self.flagged_reason = reason

        else:
            old = Review.objects.get(pk=self.pk)

            # Bloqueo de edición por el viajero
            self.rating = old.rating
            self.comment = old.comment
            self.experience_id = old.experience_id
            self.traveler_id = old.traveler_id
            self.booking_id = old.booking_id

            # Timestamp automático de respuesta del guía
            if self.guide_reply and not old.guide_reply and not self.guide_replied_at:
                self.guide_replied_at = timezone.now()

        super().save(*args, **kwargs)
