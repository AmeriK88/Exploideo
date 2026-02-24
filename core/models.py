# core/models.py
from django.db import models

class Language(models.Model):
    class Code(models.TextChoices):
        ES = "es", "Español"
        EN = "en", "English"
        DE = "de", "Deutsch"
        FR = "fr", "Français"
        IT = "it", "Italiano"
        PT = "pt", "Português"

        NL = "nl", "Nederlands"
        SV = "sv", "Svenska"
        PL = "pl", "Polski"
        DA = "da", "Dansk"
        FI = "fi", "Suomi"
        ZH = "zh", "中文 (Chinese)"

    code = models.CharField(max_length=5, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.get_code_display() # type: ignore[attr-defined]