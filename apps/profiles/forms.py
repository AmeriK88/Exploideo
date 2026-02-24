from django import forms
from core.models import Language
from .models import GuideProfile, TravelerProfile


class GuideProfileForm(forms.ModelForm):
    languages = forms.ModelMultipleChoiceField(
        queryset=Language.objects.all().order_by("code"),
        required=True,  # 👈 ponlo True si quieres obligar a elegir al menos 1 idioma
        widget=forms.CheckboxSelectMultiple,
        label="Idiomas que hablas",
    )

    class Meta:
        model = GuideProfile
        fields = [
            "display_name",
            "bio",
            "languages",
            "phone",
            "instagram",
            "website",
            "avatar",
            "guide_license_document",
            "insurance_or_registration_document",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # UX: si lo quieres como “completar perfil”, fuerza requerido solo aquí.
        # Si prefieres que sea opcional al inicio, pon required=False arriba y
        # aquí lo puedes condicionar según tu lógica.

        # Ejemplo: añade clase para tu CSS/Bootstrap si quieres
        # (CheckboxSelectMultiple no usa form-control, pero puedes meter clases)
        self.fields["languages"].widget.attrs.update({"class": "space-y-2"})

    def clean_languages(self):
        langs = self.cleaned_data.get("languages")
        if not langs or len(langs) == 0:
            raise forms.ValidationError("Selecciona al menos un idioma.")
        return langs


class TravelerProfileForm(forms.ModelForm):
    # Campos del User (cuenta)
    first_name = forms.CharField(label="Nombre", required=False, max_length=150)
    last_name = forms.CharField(label="Apellidos", required=False, max_length=150)
    email = forms.EmailField(label="Email", required=True)

    class Meta:
        model = TravelerProfile
        fields = ["display_name", "phone", "preferred_language", "country", "city"]
        labels = {
            "display_name": "Nombre público",
            "phone": "Teléfono",
            "preferred_language": "Idioma preferido",
            "country": "País",
            "city": "Ciudad",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is None:
            raise ValueError("TravelerProfileForm requires a user")
        self.user = user

        # precargar datos de User
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)

        # Guardar User
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]

        if commit:
            self.user.save()
            profile.user = self.user
            profile.save()

        return profile