from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Experience


class ExperienceForm(forms.ModelForm):
    class Meta:
        model = Experience
        fields = [
            "category",
            "title",
            "description",
            "image",
            "price",
            "duration_minutes",
            "location",
            "country",
            "region",
            "province",
            "island",
            "city",
            "transport_requirement",
            "tags",
            "difficulty",
            "is_active",
        ]

        labels = {
            "category": _("Categoría"),
            "title": _("Título"),
            "description": _("Descripción"),
            "image": _("Imagen"),
            "price": _("Precio (€)"),
            "duration_minutes": _("Duración (minutos)"),
            "location": _("Ubicación visible"),
            "country": _("País"),
            "region": _("Región"),
            "province": _("Provincia"),
            "island": _("Isla"),
            "city": _("Ciudad"),
            "transport_requirement": _("Modo de desplazamiento requerido"),
            "difficulty": _("Dificultad"),
            "is_active": _("Activa"),
        }

        help_texts = {
            "location": _("Texto descriptivo para mostrar al usuario (ej: Mirador del Rio, Lanzarote)."),
            "country": _("Opcional. País donde se realiza la experiencia."),
            "region": _("Opcional. Comunidad o región."),
            "province": _("Opcional. Provincia."),
            "island": _("Campo estructurado para filtros por isla."),
            "city": _("Campo estructurado para filtros por ciudad."),
            "difficulty": _("Define a qué público va dirigida (afecta a reservas con menores)."),
            "transport_requirement": _("Este modo lo verá el viajero y se aplicará automáticamente a nuevas reservas."),
        }

        widgets = {
            "location": forms.TextInput(attrs={"placeholder": _("Zona o punto visible para el viajero")}),
            "island": forms.TextInput(attrs={"placeholder": _("Ej: Lanzarote")}),
            "city": forms.TextInput(attrs={"placeholder": _("Ej: Teguise")}),
        }