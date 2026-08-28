from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.experiences.models import Category, Experience
from apps.messages.models import Conversation, Participant
from apps.messages.services import ensure_conversation_for_accepted_booking
from apps.profiles.models import GuideProfile
from core.models import Language


class MessagingWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.language = Language.objects.create(code="es", name="Español")
        cls.guide = User.objects.create_user(username="guide", password="pw", role=User.Role.GUIDE)
        guide_profile, _ = GuideProfile.objects.get_or_create(user=cls.guide)
        guide_profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
        guide_profile.save(update_fields=["verification_status"])
        guide_profile.languages.add(cls.language)

        cls.traveler = User.objects.create_user(username="traveler", password="pw", role=User.Role.TRAVELER)
        cls.outsider = User.objects.create_user(username="outsider", password="pw", role=User.Role.TRAVELER)
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

    def _accepted_booking(self, *, date=None):
        target_date = date or (timezone.localdate() + timedelta(days=3))
        return Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.language,
            date=target_date,
            adults=2,
            children=0,
            infants=0,
            status=Booking.Status.ACCEPTED,
            pickup_time=datetime.strptime("10:00", "%H:%M").time(),
            meeting_point="Plaza",
            transport_mode=Booking.TransportMode.ON_FOOT,
            pickup_notes="Punto",
            unit_price="50.00",
            total_price="100.00",
        )

    def test_conversation_is_created_for_accepted_booking(self):
        booking = self._accepted_booking()
        conversation = ensure_conversation_for_accepted_booking(booking)

        self.assertEqual(conversation.booking_id, booking.pk)
        self.assertEqual(conversation.status, Conversation.STATUS_ACTIVE)
        self.assertTrue(
            Participant.objects.filter(conversation=conversation, user=self.traveler, role=Participant.ROLE_TRAVELER).exists()
        )
        self.assertTrue(
            Participant.objects.filter(conversation=conversation, user=self.guide, role=Participant.ROLE_GUIDE).exists()
        )

    def test_pending_booking_has_no_conversation(self):
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.language,
            date=timezone.localdate() + timedelta(days=3),
            adults=2,
            children=0,
            infants=0,
            status=Booking.Status.PENDING,
            transport_mode=Booking.TransportMode.ON_FOOT,
            pickup_notes="Punto",
            unit_price="50.00",
            total_price="100.00",
        )

        self.assertFalse(Conversation.objects.filter(booking=booking).exists())
        self.client.force_login(self.traveler)
        response = self.client.get(reverse("messages:conversation_detail", args=[booking.pk]))
        self.assertEqual(response.status_code, 404)

    def test_canceled_booking_keeps_conversation_active_currently(self):
        booking = self._accepted_booking()
        conversation = ensure_conversation_for_accepted_booking(booking)

        booking.status = Booking.Status.CANCELED
        booking.save(update_fields=["status"])
        conversation.refresh_from_db()

        self.assertEqual(conversation.status, Conversation.STATUS_ACTIVE)

    def test_non_participant_cannot_access_or_send_messages(self):
        booking = self._accepted_booking()
        ensure_conversation_for_accepted_booking(booking)

        self.client.force_login(self.outsider)
        detail = self.client.get(reverse("messages:conversation_detail", args=[booking.pk]))
        send = self.client.post(reverse("messages:send_message", args=[booking.pk]), data={"body": "hola"})

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(send.status_code, 404)

