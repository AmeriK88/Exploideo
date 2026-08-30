from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{i} ⭐") for i in range(1, 6)],
                attrs={"class": "input"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "input",
                    "rows": 4,
                    "placeholder": _("Cuenta tu experiencia..."),
                }
            ),
        }
        labels = {
            "rating": _("Calificación"),
            "comment": _("Comentario"),
        }