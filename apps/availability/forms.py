from django import forms
from .models import ExperienceAvailability, AvailabilityBlock


WEEKDAYS = [
    ("0", "Lun"),
    ("1", "Mar"),
    ("2", "Mié"),
    ("3", "Jue"),
    ("4", "Vie"),
    ("5", "Sáb"),
    ("6", "Dom"),
]


class ExperienceAvailabilityForm(forms.ModelForm):
    """
    Form de reglas de disponibilidad para una experiencia.
    Importante:
    - weekdays se guarda como lista de ints [0..6] en JSONField
    - capacidades: vacías = sin límite
    """

    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAYS,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Si no seleccionas nada, se permitirán reservas cualquier día de la semana.",
    )

    class Meta:
        model = ExperienceAvailability
        fields = [
            "is_enabled",
            "start_date",
            "end_date",
            "daily_capacity_people",
            "daily_capacity_bookings",
            "max_people_per_booking",
            "weekdays",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "daily_capacity_people": forms.NumberInput(attrs={"min": 1, "placeholder": "Ej: 18 (vacío = sin límite)"}),
            "daily_capacity_bookings": forms.NumberInput(attrs={"min": 1, "placeholder": "Ej: 3 (vacío = sin límite)"}),
            "max_people_per_booking": forms.NumberInput(attrs={"min": 1, "placeholder": "Ej: 6 (vacío = sin límite)"}),
        }
        labels = {
            "is_enabled": "Reservas abiertas",
            "daily_capacity_people": "Capacidad diaria (personas)",
            "daily_capacity_bookings": "Max de excursiones (por día)",
            "max_people_per_booking": "Max por reserva (personas)",
        }
        help_texts = {
            "is_enabled": (
                "Actívalo para aceptar nuevas reservas. "
                "Si lo desactivas, la experiencia seguirá visible pero no permitirá reservar."
            ),
            "start_date": "Opcional. Primera fecha en la que se permiten reservas.",
            "end_date": "Opcional. Última fecha en la que se permiten reservas.",
            "daily_capacity_people": "Límite total de personas aceptadas en un mismo día. (Vacío = sin límite)",
            "daily_capacity_bookings": "Número máximo de reservas aceptadas por día. (Vacío = sin límite)",
            "max_people_per_booking": (
                "Límite de personas por reserva (por excursión). "
                "Útil si haces tours pequeños aunque el cupo diario sea mayor."
            ),
        }

    def clean_weekdays(self):
        data = self.cleaned_data.get("weekdays", [])
        return [int(x) for x in data]

    def clean(self):
        cleaned = super().clean()

        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "La fecha fin no puede ser anterior a la fecha inicio.")

        # Validaciones suaves: si meten 0 o negativo (por si se saltan min en HTML)
        for name in ("daily_capacity_people", "daily_capacity_bookings", "max_people_per_booking"):
            val = cleaned.get(name)
            if val is not None and val <= 0:
                self.add_error(name, "Debe ser un número mayor que 0, o dejarlo vacío para 'sin límite'.")

        return cleaned


class AvailabilityBlockForm(forms.ModelForm):
    class Meta:
        model = AvailabilityBlock
        fields = ["date", "reason"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "reason": forms.TextInput(attrs={"placeholder": "Ej: descanso / mal tiempo / evento privado..."}),
        }
        labels = {
            "date": "Fecha",
            "reason": "Motivo (opcional)",
        }
        help_texts = {
            "reason": "Opcional. Este texto se mostrará en tu panel para recordar por qué bloqueaste el día.",
        }

    def clean_reason(self):
        # Limpieza mínima para evitar espacios raros
        reason = (self.cleaned_data.get("reason") or "").strip()
        return reason