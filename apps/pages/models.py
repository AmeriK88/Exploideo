# pages/models.py
from django.db import models

class NewsletterSubscriber(models.Model):
    class Region(models.TextChoices):
        CANARIAS = "canarias", "Canarias"
        PENINSULA = "peninsula", "Península"
        BALEARES = "baleares", "Baleares"
        EXTRANJERO = "extranjero", "Extranjero"
        NSNC = "nsnc", "Prefiero no decirlo"

    class Island(models.TextChoices):
        LANZAROTE = "lanzarote", "Lanzarote"
        FUERTEVENTURA = "fuerteventura", "Fuerteventura"
        GRAN_CANARIA = "gran_canaria", "Gran Canaria"
        TENERIFE = "tenerife", "Tenerife"
        LA_GOMERA = "la_gomera", "La Gomera"
        LA_PALMA = "la_palma", "La Palma"
        EL_HIERRO = "el_hierro", "El Hierro"
        LA_GRACIOSA = "la_graciosa", "La Graciosa"
        OTRA = "otra", "Otra / no aplica"

    class Role(models.TextChoices):
        TRAVELER = "traveler", "Viajero"
        GUIDE = "guide", "Guía"
        BOTH = "both", "Ambos"
        NSNC = "nsnc", "No lo sé / prefiero no decirlo"

    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, blank=True, default="footer")

    # NUEVO
    region = models.CharField(max_length=20, choices=Region.choices, blank=True, default="")
    island = models.CharField(max_length=20, choices=Island.choices, blank=True, default="")
    role = models.CharField(max_length=20, choices=Role.choices, blank=True, default="")
    is_official_guide = models.BooleanField(default=False)

    # Recomendado (GDPR)
    consent = models.BooleanField(default=False)

    def __str__(self):
        return self.email
