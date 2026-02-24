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
            "difficulty",   
            "is_active",
        ]

        labels = {
            "difficulty": "Dificultad",
            "transport_requirement": "Modo de desplazamiento requerido",
        }

        help_texts = {
            "difficulty": "Define a qué público va dirigida (afecta a reservas con menores).",
            "transport_requirement": "Este modo lo verá el viajero y se aplicará automáticamente a nuevas reservas.",
        }