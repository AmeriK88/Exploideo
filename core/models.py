from django.db import models
from django.utils.translation import gettext_lazy as _

class Language(models.Model):
    class Code(models.TextChoices):
        ES = "es", _("Español")
        EN = "en", _("English")
        DE = "de", _("Deutsch")
        FR = "fr", _("Français")
        IT = "it", _("Italiano")
        PT = "pt", _("Português")

        NL = "nl", _("Nederlands")
        SV = "sv", _("Svenska")
        PL = "pl", _("Polski")
        DA = "da", _("Dansk")
        FI = "fi", _("Suomi")
        ZH = "zh", _("中文 (Chinese)")

    code = models.CharField(max_length=5, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.get_code_display() # type: ignore[attr-defined]