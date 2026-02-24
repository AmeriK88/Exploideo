from django import forms
from django.utils import timezone
from datetime import timedelta

from core.models import Language
from apps.availability.services import is_date_available
from apps.bookings.services import validate_minors_policy
from .models import Booking


class BookingForm(forms.ModelForm):
    preferred_language = forms.ModelChoiceField(
        queryset=Language.objects.none(),
        required=True,
        empty_label="Selecciona un idioma",
        label="Idioma preferido",
    )

    def __init__(self, *args, experience=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.experience = experience

        # -----------------------------
        # Idioma: filtrar por idiomas del guía (FK -> queryset)
        # -----------------------------
        allowed_qs = Language.objects.none()

        if self.experience and hasattr(self.experience.guide, "guide_profile"):
            allowed_qs = self.experience.guide.guide_profile.languages.all().order_by("code")

        self.fields["preferred_language"].queryset = allowed_qs  # type: ignore[attr-defined]

        if not allowed_qs.exists():
            self.fields["preferred_language"].help_text = "Este guía aún no ha configurado idiomas."

        # -----------------------------
        # Pickup notes según transporte
        # -----------------------------
        self.fields["pickup_notes"].label = "Tu ubicación o referencia"
        transport = getattr(experience, "transport_requirement", None)

        if transport == "own_vehicle":
            self.fields["pickup_notes"].help_text = "Indica dónde quedas con el guía (parking, punto exacto, etc.)."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Parking Mirador del Río / Gasolinera X"
        elif transport == "bicycle":
            self.fields["pickup_notes"].help_text = "Indica el punto de encuentro para comenzar la ruta en bici."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Plaza central / Tienda de bicis X"
        else:
            self.fields["pickup_notes"].help_text = "Indica el punto de encuentro para iniciar la experiencia."
            self.fields["pickup_notes"].widget.attrs["placeholder"] = "Ej: Entrada principal / Punto exacto en Maps"

    class Meta:
        model = Booking
        fields = ["date", "adults", "children", "infants", "pickup_notes", "preferred_language", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Opcional: alergias, ritmo, restricciones, necesidades, etc.",
                }
            ),
            "pickup_notes": forms.TextInput(),
        }

    def clean_preferred_language(self):
        lang = self.cleaned_data.get("preferred_language")

        if not lang:
            raise forms.ValidationError("Selecciona el idioma preferido para la experiencia.")

        if not self.experience:
            return lang

        guide_profile = getattr(self.experience.guide, "guide_profile", None)
        if not guide_profile:
            raise forms.ValidationError("El guía aún no ha configurado idiomas para esta experiencia.")

        allowed_ids = set(guide_profile.languages.values_list("id", flat=True))
        if lang.id not in allowed_ids:
            raise forms.ValidationError("Ese idioma no está disponible para este guía.")

        return lang

    def clean(self):
        cleaned = super().clean()

        adults = cleaned.get("adults") or 0
        children = cleaned.get("children") or 0
        infants = cleaned.get("infants") or 0

        if self.experience:
            try:
                validate_minors_policy(self.experience, adults, children, infants)
            except forms.ValidationError:
                raise
            except Exception as e:
                raise forms.ValidationError(str(e))

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
                self.add_error("date", "No se permiten reservas con menos de 24 hrs de antelación.")

            if self.experience:
                ok, msg = is_date_available(self.experience, date_value, people)
                if not ok:
                    self.add_error("date", msg)

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

        if self.require_pickup_time and not pickup_time:
            self.add_error("pickup_time", "Indica la hora de recogida/encuentro para aceptar la reserva.")

        if self.require_pickup_time:
            if not meeting_point and not guide_response:
                raise forms.ValidationError(
                    "Para aceptar, indica al menos el punto de encuentro o un mensaje para el viajero."
                )

        return cleaned


class BookingChangeRequestForm(forms.ModelForm):
    preferred_language = forms.ModelChoiceField(
        queryset=Language.objects.none(),
        required=True,
        empty_label="Selecciona un idioma",
        label="Idioma preferido",
    )

    class Meta:
        model = Booking
        fields = ["date", "adults", "children", "infants", "pickup_notes", "preferred_language", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "text"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, booking=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.booking = booking

        allowed_qs = Language.objects.none()
        if self.booking and hasattr(self.booking.experience.guide, "guide_profile"):
            allowed_qs = self.booking.experience.guide.guide_profile.languages.all().order_by("code")

        self.fields["preferred_language"].queryset = allowed_qs # type: ignore[attr-defined]

        if not allowed_qs.exists():
            self.fields["preferred_language"].help_text = "Este guía aún no ha configurado idiomas."

    def clean_preferred_language(self):
        lang = self.cleaned_data.get("preferred_language")

        if not lang:
            raise forms.ValidationError("Selecciona el idioma preferido para la experiencia.")

        if not self.booking:
            return lang

        guide_profile = getattr(self.booking.experience.guide, "guide_profile", None)
        if not guide_profile:
            raise forms.ValidationError("El guía aún no ha configurado idiomas para esta experiencia.")

        allowed_ids = set(guide_profile.languages.values_list("id", flat=True))
        if lang.id not in allowed_ids:
            raise forms.ValidationError("Ese idioma no está disponible para este guía.")

        return lang

    def clean(self):
        cleaned = super().clean()

        adults = cleaned.get("adults") or 0
        children = cleaned.get("children") or 0
        infants = cleaned.get("infants") or 0
        people = adults + children + infants

        if self.booking:
            try:
                validate_minors_policy(self.booking.experience, adults, children, infants)
            except forms.ValidationError:
                raise
            except Exception as e:
                raise forms.ValidationError(str(e))

        if adults <= 0:
            self.add_error("adults", "Debe haber al menos 1 adulto.")
        if people <= 0:
            raise forms.ValidationError("Debes indicar al menos 1 persona.")

        date = cleaned.get("date")
        if date:
            today = timezone.localdate()

            if date < today:
                self.add_error("date", "No puedes reservar en una fecha pasada.")

            if date <= (today + timedelta(days=1)):
                self.add_error(
                    "date",
                    "No se permiten cambios para hoy ni para mañana. Elige una fecha a partir de pasado mañana."
                )

        if self.booking and date:
            ok, msg = is_date_available(
                self.booking.experience,
                date,
                people,
                exclude_booking_id=self.booking.id,
            )
            if not ok:
                self.add_error("date", msg)

        if self.errors:
            raise forms.ValidationError("Revisa el formulario: hay campos con errores.")

        return cleaned