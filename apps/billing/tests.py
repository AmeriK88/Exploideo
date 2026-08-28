from datetime import datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Invoice, InvoiceItem
from apps.billing.services import create_invoice_from_booking
from apps.billing.services_rectification import create_rectificative_for_invoice
from apps.bookings.models import Booking
from apps.experiences.models import Category, Experience
from apps.profiles.models import GuideProfile
from core.models import Language


class BillingServiceTests(TestCase):
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

    def _accepted_booking(self, *, adults=2, children=1, date=None):
        target_date = date or (timezone.localdate() + timedelta(days=4))
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.language,
            date=target_date,
            adults=adults,
            children=children,
            infants=0,
            status=Booking.Status.ACCEPTED,
            pickup_time=datetime.strptime("10:00", "%H:%M").time(),
            meeting_point="Plaza",
            transport_mode=Booking.TransportMode.ON_FOOT,
            pickup_notes="Punto",
            unit_price=Decimal("50.00"),
            total_price=Decimal("125.00"),
        )
        booking.refresh_from_db()
        return booking

    def test_create_invoice_from_booking_is_idempotent(self):
        booking = self._accepted_booking()

        first = create_invoice_from_booking(booking)
        second = create_invoice_from_booking(booking)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Invoice.objects.filter(booking=booking).count(), 1)

    def test_rectificative_invoice_annuls_original_invoice(self):
        booking = self._accepted_booking()
        invoice = create_invoice_from_booking(booking)

        rect = create_rectificative_for_invoice(invoice, reason="Cancelación")

        self.assertEqual(rect.kind, Invoice.Kind.RECTIFICATIVE)
        self.assertEqual(rect.rectifies_id, invoice.pk)
        self.assertIsNone(rect.booking)
        self.assertEqual(rect.customer_id, invoice.customer_id)
        self.assertEqual(rect.total, -invoice.total)
        self.assertTrue(InvoiceItem.objects.filter(invoice=rect).exists())
