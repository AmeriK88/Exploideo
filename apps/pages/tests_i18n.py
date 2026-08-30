from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.experiences.models import Category, CategoryTranslation, Experience, ExperienceTranslation
from core.models import Language


class InternationalizationTests(TestCase):
    def setUp(self):
        self.lang_es = Language.objects.create(code="es", name="Español")
        self.lang_en = Language.objects.create(code="en", name="English")

        self.guide = User.objects.create_user(username="guide_i18n", password="pw", role=User.Role.GUIDE)
        self.traveler = User.objects.create_user(username="traveler_i18n", password="pw", role=User.Role.TRAVELER)

        self.category = Category.objects.create(name="Senderismo", slug="senderismo")
        CategoryTranslation.objects.create(category=self.category, language="en", name="Hiking")

        self.experience = Experience.objects.create(
            guide=self.guide,
            category=self.category,
            title="Caminata por los volcanes",
            description="Una ruta increíble por paisajes volcánicos.",
            price=Decimal("45.00"),
            duration_minutes=120,
            difficulty=Experience.Difficulty.EASY,
            transport_requirement=Experience.TransportRequirement.ON_FOOT,
            location="Timanfaya",
        )
        ExperienceTranslation.objects.create(
            experience=self.experience,
            language="en",
            title="Volcano Walk",
            description="An incredible trail through volcanic landscapes.",
        )

    def test_choices_display_localization(self):
        with translation.override("es"):
            self.assertEqual(str(self.experience.get_difficulty_display()), "Fácil")
            self.assertEqual(str(self.experience.get_transport_requirement_display()), "A pie")

        with translation.override("en"):
            self.assertEqual(str(self.experience.get_difficulty_display()), "Easy")
            self.assertEqual(str(self.experience.get_transport_requirement_display()), "On foot")

    def test_dynamic_db_content_translation_and_fallback(self):
        # ES locale returns original
        with translation.override("es"):
            self.assertEqual(self.experience.translated_title, "Caminata por los volcanes")
            self.assertEqual(self.experience.translated_description, "Una ruta increíble por paisajes volcánicos.")

        # EN locale returns translation
        with translation.override("en"):
            self.assertEqual(self.experience.translated_title, "Volcano Walk")
            self.assertEqual(self.experience.translated_description, "An incredible trail through volcanic landscapes.")

        # Missing locale (e.g. "de") falls back smoothly to original without 500
        with translation.override("de"):
            self.assertEqual(self.experience.translated_title, "Caminata por los volcanes")

    def test_page_renders_in_selected_language(self):
        # Test ES URL
        response_es = self.client.get(reverse("experiences:list"))
        self.assertEqual(response_es.status_code, 200)
        self.assertContains(response_es, "Descubre experiencias")

        # Test EN URL
        with translation.override("en"):
            url_en = reverse("experiences:list")
        response_en = self.client.get(url_en)
        self.assertEqual(response_en.status_code, 200)
        self.assertContains(response_en, "Explore routes, volcanoes, coves and unique plans with local guides.")

    def test_language_switch_does_not_mutate_stored_data(self):
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            date="2026-10-15",
            adults=2,
            transport_mode=Booking.TransportMode.OWN_VEHICLE,
            preferred_language=self.lang_es,
            status=Booking.Status.ACCEPTED,
        )

        with translation.override("en"):
            # Check display label in EN
            self.assertEqual(str(booking.get_status_display()), "Accepted")

        # Refresh from DB and verify raw persistent status value is unchanged
        booking.refresh_from_db()
        self.assertEqual(booking.status, "accepted")
        self.assertEqual(booking.adults, 2)
