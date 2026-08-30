from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import translation
from django.utils.translation import gettext_lazy as _


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.get_name()

    def get_name(self, lang: str = None) -> str:
        if lang is None:
            lang = translation.get_language() or "es"
        if lang.startswith("es"):
            return self.name
        t = self.translations.filter(language=lang).first()
        return (t.name if t and t.name else self.name)

    @property
    def translated_name(self) -> str:
        return self.get_name()


class Experience(models.Model):
    guide = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="experiences",
        limit_choices_to={"role": "guide"},
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="experiences",
    )

    class TransportRequirement(models.TextChoices):
        OWN_VEHICLE = "own_vehicle", _("Vehículo propio")
        BICYCLE = "bicycle", _("Bicicleta")
        ON_FOOT = "on_foot", _("A pie")

    transport_requirement = models.CharField(
        max_length=20,
        choices=TransportRequirement.choices,
        default=TransportRequirement.ON_FOOT,
    )

    class Difficulty(models.TextChoices):
        EASY = "easy", _("Fácil")
        MODERATE = "moderate", _("Moderada")
        HARD = "hard", _("Difícil")

    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()
    max_people = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True, default="España")
    region = models.CharField(max_length=120, blank=True, default="")
    province = models.CharField(max_length=120, blank=True, default="")
    island = models.CharField(max_length=120, blank=True, default="", db_index=True)
    city = models.CharField(max_length=120, blank=True, default="", db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    image = models.ImageField(upload_to="experiences/", blank=True, null=True)


    # NUEVO: keywords/tags para búsquedas
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Palabras clave separadas por comas. Ej: timanfaya, volcanes, lava",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    DIFFICULTY_BANNER_MAP = {
        Difficulty.EASY: {
            "icon": "✔",
            "tone": "success",
            "title": "Nivel fácil",
            "message": "Apta para todos los públicos.",
        },
        Difficulty.MODERATE: {
            "icon": "⚠️",
            "tone": "warning",
            "title": "Nivel moderado",
            "message": "Menores permitidos solo acompañados por adultos.",
        },
        Difficulty.HARD: {
            "icon": "⛔",
            "tone": "danger",
            "title": "Nivel difícil",
            "message": "Experiencia difícil: no se permiten menores.",
        },
    }

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["price"]),
            models.Index(fields=["duration_minutes"]),
            models.Index(fields=["island", "city"], name="experiences_island_a8cc5d_idx"),
        ]

    def clean(self):
        super().clean()

        latitude = self.latitude
        longitude = self.longitude
        has_latitude = latitude is not None
        has_longitude = longitude is not None

        if has_latitude != has_longitude:
            raise ValidationError(
                {
                    "latitude": "Debes informar latitud y longitud juntas.",
                    "longitude": "Debes informar latitud y longitud juntas.",
                }
            )

        if has_latitude and not (-90 <= latitude <= 90):
            raise ValidationError({"latitude": "La latitud debe estar entre -90 y 90."})

        if has_longitude and not (-180 <= longitude <= 180):
            raise ValidationError({"longitude": "La longitud debe estar entre -180 y 180."})

    @property
    def is_georeferenced(self):
        return self.latitude is not None and self.longitude is not None

    @property
    def structured_location(self):
        parts = [self.city, self.island, self.region, self.country]
        return ", ".join(part for part in parts if part)

    @property
    def difficulty_banner(self):
        config = self.DIFFICULTY_BANNER_MAP.get(
            self.difficulty,
            self.DIFFICULTY_BANNER_MAP[self.Difficulty.EASY],
        )
        return {
            **config,
            "css_class": f"c-alert c-alert--{config['tone']}",
        }

    def get_title(self, lang: str = None) -> str:
        if lang is None:
            lang = translation.get_language() or "es"
        if lang.startswith("es"):
            return self.title
        t = self.translations.filter(language=lang).first()
        return (t.title if t and t.title else self.title)

    def get_description(self, lang: str = None) -> str:
        if lang is None:
            lang = translation.get_language() or "es"
        if lang.startswith("es"):
            return self.description
        t = self.translations.filter(language=lang).first()
        return (t.description if t and t.description else self.description)

    @property
    def translated_title(self) -> str:
        return self.get_title()

    @property
    def translated_description(self) -> str:
        return self.get_description()

    def __str__(self):
        return f"{self.translated_title} - {self.guide.username}"


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language = models.CharField(max_length=5, db_index=True)
    name = models.CharField(max_length=80)

    class Meta:
        unique_together = [("category", "language")]
        verbose_name = _("Traducción de categoría")
        verbose_name_plural = _("Traducciones de categoría")

    def __str__(self):
        return f"{self.category.name} [{self.language}]"


class ExperienceTranslation(models.Model):
    experience = models.ForeignKey(
        Experience,
        on_delete=models.CASCADE,
        related_name="translations",
    )
    language = models.CharField(max_length=5, db_index=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_machine_translated = models.BooleanField(default=True)
    is_outdated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("experience", "language")]
        verbose_name = _("Traducción de experiencia")
        verbose_name_plural = _("Traducciones de experiencia")

    def __str__(self):
        return f"{self.experience.title} [{self.language}]"
