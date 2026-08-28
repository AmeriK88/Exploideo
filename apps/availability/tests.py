from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.availability.models import ExperienceAvailability, AvailabilityBlock
from apps.availability.services import is_date_available
from apps.bookings.models import Booking
from apps.experiences.models import Category, Experience
from apps.profiles.models import GuideProfile
from core.models import Language


class AvailabilityServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(code="es", name="Español")
        cls.guide = User.objects.create_user(username="guide", password="pw", role=User.Role.GUIDE)
        guide_profile, _ = GuideProfile.objects.get_or_create(user=cls.guide)
        guide_profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
        guide_profile.save(update_fields=["verification_status"])
        guide_profile.languages.add(cls.language)

        cls.traveler = User.objects.create_user(username="traveler", password="pw", role=User.Role.TRAVELER)
        cls.category = Category.objects.create(name="Senderismo", slug="senderismo")
        cls.experience = Experience.objects.create(
            guide=cls.guide,
            category=cls.category,
            title="Ruta volcánica",
            description="Desc",
            price="50.00",
            duration_minutes=120,
            location="Lugar",
            country="España",
            island="Lanzarote",
            city="Teguise",
            transport_requirement=Experience.TransportRequirement.ON_FOOT,
            difficulty=Experience.Difficulty.EASY,
        )
        cls.availability = ExperienceAvailability.objects.create(
            experience=cls.experience,
            daily_capacity_people=4,
            daily_capacity_bookings=2,
            max_people_per_booking=3,
            weekdays=[0, 1, 2, 3, 4, 5, 6],
        )

    def _booking(self, *, status, people, date):
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.language,
            date=date,
            adults=people,
            children=0,
            infants=0,
            status=status,
            unit_price="50.00",
            total_price="50.00" if people == 1 else str(50 * people),
            transport_mode=Booking.TransportMode.ON_FOOT,
            pickup_notes="Punto de encuentro",
        )
        booking.refresh_from_db()
        return booking

    def test_accepted_bookings_consume_capacity(self):
        target = timezone.localdate() + timedelta(days=3)
        self._booking(status=Booking.Status.ACCEPTED, people=3, date=target)

        ok, message = is_date_available(self.experience, target, 2)

        self.assertFalse(ok)
        self.assertIn("capacidad", message.lower())

    def test_pending_bookings_do_not_consume_capacity(self):
        target = timezone.localdate() + timedelta(days=3)
        self._booking(status=Booking.Status.PENDING, people=3, date=target)

        ok, message = is_date_available(self.experience, target, 2)

        self.assertTrue(ok, message)

    def test_blocked_date_is_unavailable(self):
        target = timezone.localdate() + timedelta(days=4)
        block = AvailabilityBlock.objects.create(
            availability=self.availability,
            date=target,
            reason="Descanso",
        )

        ok, message = is_date_available(self.experience, target, 2)

        self.assertFalse(ok)
        self.assertIn("bloqueada", message.lower())
        self.assertEqual(block.availability, self.availability)

    def test_outside_date_range_is_unavailable(self):
        target = timezone.localdate() + timedelta(days=4)
        self.availability.start_date = target + timedelta(days=1)
        self.availability.save(update_fields=["start_date"])

        ok, message = is_date_available(self.experience, target, 2)

        self.assertFalse(ok)
        self.assertIn("rango", message.lower())
