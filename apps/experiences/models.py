from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models



class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


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
        OWN_VEHICLE = "own_vehicle", "Vehículo propio"
        BICYCLE = "bicycle", "Bicicleta"
        ON_FOOT = "on_foot", "A pie"

    transport_requirement = models.CharField(
        max_length=20,
        choices=TransportRequirement.choices,
        default=TransportRequirement.ON_FOOT,
    )

    class Difficulty(models.TextChoices):
        EASY = "easy", "Fácil"
        MODERATE = "moderate", "Moderada"
        HARD = "hard", "Difícil"

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

    def __str__(self):
        return f"{self.title} - {self.guide.username}"
