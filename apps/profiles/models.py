from django.conf import settings
from django.db import models
from core.models import Language


class GuideProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guide_profile",
        limit_choices_to={"role": "guide"},
    )

    avatar = models.ImageField(
        upload_to="guides/avatars/",
        blank=True,
        null=True,
        help_text="Foto de perfil (JPG/PNG)."
    )

    languages = models.ManyToManyField(
        Language,
        blank=True,
        related_name="guide_profiles",
    )

    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    instagram = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)

    # --- Verificación: documentos ---
    guide_license_document = models.FileField(
        upload_to="verification/guide_license/",
        blank=True,
        null=True,
        help_text="Carnet/acreditación oficial de guía (PDF/JPG/PNG).",
    )
    insurance_or_registration_document = models.FileField(
        upload_to="verification/insurance_or_registration/",
        blank=True,
        null=True,
        help_text="Seguro RC o alta de autónomo/empresa (PDF/JPG/PNG).",
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    verification_notes = models.TextField(
        blank=True,
        help_text="Notas internas (motivo de rechazo, observaciones, etc.).",
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="verified_guides",
        help_text="Admin/Staff que verificó el perfil.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GuideProfile({self.user.username})"


class TravelerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="traveler_profile",
        limit_choices_to={"role": "traveler"},
    )

    display_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    preferred_language = models.CharField(max_length=20, blank=True)  # ej: "es", "en"
    country = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=120, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TravelerProfile({self.user.username})"

