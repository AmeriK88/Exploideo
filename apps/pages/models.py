# pages/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class NewsletterSubscriber(models.Model):
    class Region(models.TextChoices):
        CANARIAS = "canarias", _("Canarias")
        PENINSULA = "peninsula", _("Península")
        BALEARES = "baleares", _("Baleares")
        EXTRANJERO = "extranjero", _("Extranjero")
        NSNC = "nsnc", _("Prefiero no decirlo")

    class Island(models.TextChoices):
        LANZAROTE = "lanzarote", _("Lanzarote")
        FUERTEVENTURA = "fuerteventura", _("Fuerteventura")
        GRAN_CANARIA = "gran_canaria", _("Gran Canaria")
        TENERIFE = "tenerife", _("Tenerife")
        LA_GOMERA = "la_gomera", _("La Gomera")
        LA_PALMA = "la_palma", _("La Palma")
        EL_HIERRO = "el_hierro", _("El Hierro")
        LA_GRACIOSA = "la_graciosa", _("La Graciosa")
        OTRA = "otra", _("Otra / no aplica")

    class Role(models.TextChoices):
        TRAVELER = "traveler", _("Viajero")
        GUIDE = "guide", _("Guía")
        BOTH = "both", _("Ambos")
        NSNC = "nsnc", _("No lo sé / prefiero no decirlo")

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
