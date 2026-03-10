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
            "country",
            "region",
            "province",
            "island",
            "city",
            "latitude",
            "longitude",
            "transport_requirement",
            "tags",
            "difficulty",
            "is_active",
        ]

        labels = {
            "location": "Ubicación visible",
            "country": "País",
            "region": "Región",
            "province": "Provincia",
            "island": "Isla",
            "city": "Ciudad",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "difficulty": "Dificultad",
            "transport_requirement": "Modo de desplazamiento requerido",
        }

        help_texts = {
            "location": "Texto descriptivo para mostrar al usuario (ej: Mirador del Rio, Lanzarote).",
            "country": "Opcional. País donde se realiza la experiencia.",
            "region": "Opcional. Comunidad o región.",
            "province": "Opcional. Provincia.",
            "island": "Campo estructurado para filtros por isla.",
            "city": "Campo estructurado para filtros por ciudad.",
            "latitude": "Opcional. Úsala junto con longitud para futuras búsquedas por cercanía.",
            "longitude": "Opcional. Úsala junto con latitud para futuras búsquedas por cercanía.",
            "difficulty": "Define a qué público va dirigida (afecta a reservas con menores).",
            "transport_requirement": "Este modo lo verá el viajero y se aplicará automáticamente a nuevas reservas.",
        }

        widgets = {
            "location": forms.TextInput(attrs={"placeholder": "Zona o punto visible para el viajero"}),
            "island": forms.TextInput(attrs={"placeholder": "Ej: Lanzarote"}),
            "city": forms.TextInput(attrs={"placeholder": "Ej: Teguise"}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "Ej: 29.046853"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "Ej: -13.589973"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get("latitude")
        longitude = cleaned_data.get("longitude")

        if (latitude is None) != (longitude is None):
            error = "Debes rellenar latitud y longitud juntas."
            self.add_error("latitude", error)
            self.add_error("longitude", error)

        return cleaned_data