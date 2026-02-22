from django import forms
from apps.availability.services import is_date_available
from .models import Booking
from django.utils import timezone
from datetime import timedelta



class BookingForm(forms.ModelForm):
    def __init__(self, *args, experience=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.experience = experience

        # Idioma obligatorio + mantiene el "Selecciona un idioma"
        self.fields["preferred_language"].choices = list(self.fields["preferred_language"].choices)
        self.fields["preferred_language"].required = True

        # --- Pickup / meeting notes: depende del transporte que requiere la experience ---
        self.fields["pickup_notes"].label = "Tu ubicación o referencia"  
        transport = getattr(experience, "transport_requirement", None)

        if transport == "own_vehicle":
            self.fields["pickup_notes"].help_text = "Indica dónde quedas con el guía (parking, punto exacto, etc.)."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Parking Mirador del Río / Gasolinera X"
        elif transport == "bicycle":
            self.fields["pickup_notes"].help_text = "Indica el punto de encuentro para comenzar la ruta en bici."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Plaza central / Tienda de bicis X"
        else:  # on_foot o cualquier otro
            self.fields["pickup_notes"].help_text = "Indica el punto de encuentro para iniciar la experiencia."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Entrada principal / Punto exacto en Maps"

    class Meta:
        model = Booking
        fields = ["date", "adults", "children", "infants", "pickup_notes", "preferred_language", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Opcional: alergias, ritmo, restricciones, necesidades, etc."
            }),
            "pickup_notes": forms.TextInput(),
        }

    def clean(self):
        cleaned = super().clean()

        adults = cleaned.get("adults") or 0
        children = cleaned.get("children") or 0
        infants = cleaned.get("infants") or 0

        if adults <= 0:
            self.add_error("adults", "Debe haber al menos 1 adulto.")

        people = adults + children + infants
        if people <= 0:
            raise forms.ValidationError("Debes indicar al menos 1 persona.")

        date_value = cleaned.get("date")
        if date_value:
            today = timezone.localdate()

            if date_value < today:
                self.add_error("date", "No puedes reservar en una fecha pasada.")

            if date_value <= today + timedelta(days=1):
                self.add_error(
                    "date",
                    "No se permiten reservas con menos de 24 hrs de antelación."
                )

            # Disponibilidad
            if self.experience:
                ok, msg = is_date_available(self.experience, date_value, people)
                if not ok:
                    self.add_error("date", msg)

        if not cleaned.get("preferred_language"):
            self.add_error("preferred_language", "Selecciona el idioma preferido para la experiencia.")

        pickup_notes = (cleaned.get("pickup_notes") or "").strip()
        if not pickup_notes:
            self.add_error("pickup_notes", "Indica el punto de encuentro (lo concretarás con el guía si hace falta).")

        if self.errors:
            raise forms.ValidationError("Revisa el formulario: hay campos con errores.")

        return cleaned


class BookingDecisionForm(forms.ModelForm):
    require_pickup_time = False
    require_guide_response = False

    class Meta:
        model = Booking
        fields = ["pickup_time", "meeting_point", "guide_response"]
        widgets = {
            "pickup_time": forms.TimeInput(attrs={"type": "time"}),
            "meeting_point": forms.TextInput(attrs={"placeholder": "Ej: Lobby Hotel X / Parking Y"}),
            "guide_response": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        cleaned = super().clean()

        pickup_time = cleaned.get("pickup_time")
        meeting_point = (cleaned.get("meeting_point") or "").strip()
        guide_response = (cleaned.get("guide_response") or "").strip()
        if self.require_guide_response and not guide_response:
            self.add_error("guide_response", "Indica un motivo para rechazar la reserva.")

        # Si se acepta: pickup_time obligatorio
        if self.require_pickup_time and not pickup_time:
            self.add_error(
                "pickup_time",
                "Indica la hora de recogida/encuentro para aceptar la reserva."
            )

        # Si se acepta: al menos meeting_point o guide_response
        if self.require_pickup_time:
            if not meeting_point and not guide_response:
                # Puedes elegir dónde mostrarlo:
                # 1) error general:
                raise forms.ValidationError(
                    "Para aceptar, indica al menos el punto de encuentro o un mensaje para el viajero."
                )
                # 2) o si prefieres errores por campo:
                # self.add_error("meeting_point", "Indica el punto o añade un mensaje.")
                # self.add_error("guide_response", "Indica el punto o añade un mensaje.")
        return cleaned


class BookingChangeRequestForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ["date", "adults", "children", "infants", "pickup_notes", "preferred_language", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking

    def clean(self):
        cleaned = super().clean()

        adults = cleaned.get("adults") or 0
        children = cleaned.get("children") or 0
        infants = cleaned.get("infants") or 0
        people = adults + children + infants

        if adults <= 0:
            self.add_error("adults", "Debe haber al menos 1 adulto.")
        if people <= 0:
            raise forms.ValidationError("Debes indicar al menos 1 persona.")

        date = cleaned.get("date")
        if date:
            today = timezone.localdate()

            if date < today:
                self.add_error("date", "No puedes reservar en una fecha pasada.")

            # Bloquear hoy y mañana (pasado mañana en adelante)
            if date <= (today + timedelta(days=1)):
                self.add_error(
                    "date",
                    "No se permiten cambios para hoy ni para mañana. Elige una fecha a partir de pasado mañana."
                )

        # disponibilidad con exclude_booking_id
        if self.booking and date:
            ok, msg = is_date_available(
                self.booking.experience,
                date,
                people,
                exclude_booking_id=self.booking.id,
            )
            if not ok:
                self.add_error("date", msg)
        
        # Mensaje global si hay cualquier error
        if self.errors:
            raise forms.ValidationError("Revisa el formulario: hay campos con errores.")
        return cleaned

