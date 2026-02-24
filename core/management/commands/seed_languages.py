# core/management/commands/seed_languages.py
from django.core.management.base import BaseCommand
from core.models import Language

class Command(BaseCommand):
    help = "Crea/actualiza idiomas base en core.Language"

    def handle(self, *args, **options):
        # code: name
        data = {
            "es": "Español",
            "en": "English",
            "de": "Deutsch",
            "fr": "Français",
            "it": "Italiano",
            "pt": "Português",
            "nl": "Nederlands",
            "sv": "Svenska",
            "pl": "Polski",
            "da": "Dansk",
            "fi": "Suomi",
            "zh": "中文 (Chinese)",
        }

        created = 0
        updated = 0

        for code, name in data.items():
            obj, was_created = Language.objects.update_or_create(
                code=code,
                defaults={"name": name},
            )
            created += int(was_created)
            updated += int(not was_created)

        self.stdout.write(self.style.SUCCESS(
            f"OK — creados: {created}, actualizados: {updated}"
        ))