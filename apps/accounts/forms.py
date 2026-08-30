from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(choices=User.Role.choices, label=_("Rol"))

    class Meta:
        model = User
        fields = ("username", "email", "role", "password1", "password2")
        labels = {
            "username": _("Nombre de usuario"),
            "email": _("Correo electrónico"),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.email = (user.email or "").lower()
        if commit:
            user.save()
        return user
    
DELETE_PHRASE = "ELIMINAR PERMANENTEMENTE"

class DeleteAccountForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        label=_("Entiendo que esta acción es permanente y desactiva mi cuenta.")
    )
    phrase = forms.CharField(
        required=True,
        label=_('Escribe "ELIMINAR PERMANENTEMENTE" para confirmar'),
        help_text=_("Esto evita eliminaciones accidentales."),
        widget=forms.TextInput(attrs={"autocomplete": "off"})
    )

    def clean_phrase(self):
        value = (self.cleaned_data.get("phrase") or "").strip().upper()
        if value != DELETE_PHRASE:
            raise ValidationError(_('Debes escribir exactamente: ELIMINAR PERMANENTEMENTE'))
        return value
