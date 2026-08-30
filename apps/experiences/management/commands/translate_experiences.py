from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from apps.experiences.models import Experience, ExperienceTranslation, Category, CategoryTranslation


# Basic translation dictionary / logic for seed/existing categories and title terms
CATEGORY_TRANSLATIONS = {
    "Senderismo": "Hiking",
    "Volcanes": "Volcanoes",
    "Gastro local": "Local Gastronomy",
    "Costa y calas": "Coast & Coves",
    "Atardecer": "Sunset",
    "Aventura": "Adventure",
}

TITLE_REPLACEMENTS = [
    ("Ruta por los volcanes de Timanfaya", "Route through Timanfaya Volcanoes"),
    ("Paseo en barco por las calas de Papagayo", "Boat trip around Papagayo Coves"),
    ("Senderismo al atardecer en el Volcán de Cuervo", "Sunset hiking at Cuervo Volcano"),
    ("Cata de vinos y quesos de La Geria", "Wine and cheese tasting in La Geria"),
]


def auto_translate_text(text: str, target_lang: str) -> str:
    if not text:
        return ""
    if target_lang == "en":
        # Check title replacements
        for es, en in TITLE_REPLACEMENTS:
            if es.lower() in text.lower():
                return text.replace(es, en)
        # Word replacements
        res = text
        for es, en in [
            ("Senderismo", "Hiking"),
            ("Volcanes", "Volcanoes"),
            ("Ruta", "Trail"),
            ("atardecer", "sunset"),
            ("Cata de vinos", "Wine tasting"),
            ("Aventura", "Adventure"),
            ("Fácil", "Easy"),
            ("Moderado", "Moderate"),
            ("Difícil", "Hard"),
        ]:
            res = res.replace(es, en)
        return res
    return text


class Command(BaseCommand):
    help = "Generates missing translations for existing experiences and categories."

    def add_arguments(self, parser):
        parser.add_argument(
            "-l", "--language",
            default="en",
            help="Target language code (default: 'en').",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate backfill without writing to database.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing human translations.",
        )

    def handle(self, *args, **options):
        lang = options["language"]
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(f"Starting experience translation backfill for language '{lang}'...")

        # 1. Translate categories
        categories = Category.objects.all()
        cat_created = 0
        cat_updated = 0

        for cat in categories:
            trans = CategoryTranslation.objects.filter(category=cat, language=lang).first()
            translated_name = CATEGORY_TRANSLATIONS.get(cat.name, cat.name)

            if not trans:
                cat_created += 1
                if not dry_run:
                    CategoryTranslation.objects.create(
                        category=cat,
                        language=lang,
                        name=translated_name,
                    )
            elif force or trans.name != translated_name:
                cat_updated += 1
                if not dry_run:
                    trans.name = translated_name
                    trans.save(update_fields=["name"])

        # 2. Translate experiences
        experiences = Experience.objects.all()
        exp_created = 0
        exp_updated = 0
        exp_skipped = 0
        exp_failed = 0

        for exp in experiences:
            try:
                trans = ExperienceTranslation.objects.filter(experience=exp, language=lang).first()

                if trans and not trans.is_machine_translated and not force:
                    exp_skipped += 1
                    continue

                translated_title = auto_translate_text(exp.title, lang)
                translated_desc = auto_translate_text(exp.description, lang)

                if not trans:
                    exp_created += 1
                    if not dry_run:
                        ExperienceTranslation.objects.create(
                            experience=exp,
                            language=lang,
                            title=translated_title,
                            description=translated_desc,
                            is_machine_translated=True,
                            is_outdated=False,
                        )
                else:
                    exp_updated += 1
                    if not dry_run:
                        trans.title = translated_title
                        trans.description = translated_desc
                        trans.is_machine_translated = True
                        trans.is_outdated = False
                        trans.save(update_fields=["title", "description", "is_machine_translated", "is_outdated", "updated_at"])

            except Exception as e:
                exp_failed += 1
                self.stderr.write(f"Failed to translate experience #{exp.pk}: {e}")

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Backfill complete!\n"
            f"- Categories created: {cat_created}, updated: {cat_updated}\n"
            f"- Experiences created: {exp_created}, updated: {exp_updated}, skipped (human edited): {exp_skipped}, failed: {exp_failed}"
        ))
