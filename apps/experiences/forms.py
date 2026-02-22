from django import forms
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
            "transport_requirement",
            "tags",
            "is_active",
        ]

        labels = {
            "transport_requirement": "Modo de desplazamiento requerido",
        }

        help_texts = {
            "transport_requirement": (
                "Este modo lo verá el viajero y se aplicará automáticamente a nuevas reservas."
            ),
        }