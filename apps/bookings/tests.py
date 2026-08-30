from datetime import datetime, timedelta
from decimal import Decimal
from unittest import expectedFailure
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.availability.models import ExperienceAvailability, AvailabilityBlock
from apps.billing.models import Invoice
from apps.billing.services import create_invoice_from_booking
from apps.bookings.models import Booking
from apps.experiences.models import Category, Experience
from apps.messages.models import Conversation, Participant
from apps.profiles.models import GuideProfile
from core.models import Language


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BookingWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lang_es = Language.objects.create(code="es", name="Español")
        cls.lang_en = Language.objects.create(code="en", name="English")

        cls.guide = User.objects.create_user(username="guide", email="guide@example.com", password="pw", role=User.Role.GUIDE)
        guide_profile, _ = GuideProfile.objects.get_or_create(user=cls.guide)
        guide_profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
        guide_profile.save(update_fields=["verification_status"])
        guide_profile.languages.add(cls.lang_es, cls.lang_en)

        cls.traveler = User.objects.create_user(username="traveler", email="traveler@example.com", password="pw", role=User.Role.TRAVELER)
        cls.other_traveler = User.objects.create_user(username="other", password="pw", role=User.Role.TRAVELER)
        cls.category = Category.objects.create(name="Senderismo", slug="senderismo")
        cls.experience = Experience.objects.create(
            guide=cls.guide,
            category=cls.category,
            title="Ruta volcánica",
            description="Desc",
            price="40.00",
            duration_minutes=120,
            location="Lugar",
            country="España",
            island="Lanzarote",
            city="Teguise",
            transport_requirement=Experience.TransportRequirement.BICYCLE,
            difficulty=Experience.Difficulty.EASY,
        )
        cls.availability = ExperienceAvailability.objects.create(
            experience=cls.experience,
            weekdays=[0, 1, 2, 3, 4, 5, 6],
            daily_capacity_people=20,
            daily_capacity_bookings=5,
            max_people_per_booking=6,
        )

    def setUp(self):
        Booking.objects.all().delete()
        AvailabilityBlock.objects.all().delete()
        mail.outbox = []

    def _booking_date(self):
        return timezone.localdate() + timedelta(days=3)

    def _post_create_booking(self, *, adults=2, children=1, infants=0, date=None, preferred_language=None, notes="Sin alergias", pickup_notes="Parking del puerto"):
        self.client.force_login(self.traveler)
        target_date = date or self._booking_date()
        lang_id = preferred_language.pk if preferred_language else self.lang_es.pk
        response = self.client.post(
            reverse("bookings:create", args=[self.experience.pk]),
            data={
                "date": target_date.isoformat(),
                "adults": adults,
                "children": children,
                "infants": infants,
                "pickup_notes": pickup_notes,
                "preferred_language": str(lang_id),
                "notes": notes,
            },
        )
        return response

    def _create_booking(self, **kwargs):
        response = self._post_create_booking(**kwargs)
        self.assertEqual(response.status_code, 302)
        booking = (
            Booking.objects.filter(
                traveler=self.traveler,
                experience=self.experience,
                date=kwargs.get("date") or self._booking_date(),
            )
            .order_by("-pk")
            .first()
        )
        self.assertIsNotNone(booking)
        return booking

    def _create_accepted_booking(self, *, adults=2, children=0, infants=0, date=None):
        booking = self._create_booking(adults=adults, children=children, infants=infants, date=date)
        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:accept", args=[booking.pk]),
            data={
                "pickup_time": "10:00",
                "meeting_point": "Plaza principal",
                "guide_response": "Confirmado",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return booking

    def _request_change(self, booking, *, date=None, adults=None, children=None, infants=None):
        self.client.force_login(self.traveler)
        response = self.client.post(
            reverse("bookings:request_change", args=[booking.pk]),
            data={
                "date": (date or booking.date).isoformat(),
                "adults": adults if adults is not None else booking.adults,
                "children": children if children is not None else booking.children,
                "infants": infants if infants is not None else booking.infants,
                "pickup_notes": "Nuevo punto",
                "preferred_language": str(self.lang_en.pk),
                "notes": "Cambio solicitado",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return booking

    def _accept_change(self, booking):
        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:guide_change_decide", args=[booking.pk, "accept"]),
            data={},
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return response, booking

    def _reject_change(self, booking):
        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:guide_change_decide", args=[booking.pk, "reject"]),
            data={},
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return response, booking

    def _request_cancel(self, booking, reason="Cambio de planes"):
        self.client.force_login(self.traveler)
        response = self.client.post(
            reverse("bookings:request_cancel", args=[booking.pk]),
            data={"reason": reason},
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return booking

    def _decide_cancel(self, booking, decision):
        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:guide_cancel_decide", args=[booking.pk, decision]),
            data={},
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        return booking

    def test_booking_creation_sets_snapshot_and_people(self):
        booking = self._create_booking(adults=2, children=1, infants=1)

        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.adults, 2)
        self.assertEqual(booking.children, 1)
        self.assertEqual(booking.infants, 1)
        self.assertEqual(booking.people, 4)
        self.assertEqual(booking.preferred_language, self.lang_es)
        self.assertEqual(booking.transport_mode, Booking.TransportMode.BICYCLE)
        self.assertEqual(booking.unit_price, booking.experience.price)
        self.assertEqual(booking.total_price, Decimal("100.00"))

        self.experience.transport_requirement = Experience.TransportRequirement.ON_FOOT
        self.experience.save(update_fields=["transport_requirement"])
        booking.refresh_from_db()
        self.assertEqual(booking.transport_mode, Booking.TransportMode.BICYCLE)

    def test_booking_price_is_snapshotted_after_creation(self):
        booking = self._create_booking(adults=2, children=1, infants=0)
        original_total = booking.total_price

        self.experience.price = "99.00"
        self.experience.save(update_fields=["price"])

        booking.refresh_from_db()
        self.assertEqual(booking.total_price, original_total)
        self.assertEqual(booking.unit_price, Decimal("40.00"))

    def test_booking_creation_rejects_capacity_over_limit(self):
        self.availability.max_people_per_booking = 3
        self.availability.save(update_fields=["max_people_per_booking"])

        response = self._post_create_booking(adults=4, children=0, infants=0)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Máximo por excursión")
        self.assertFalse(Booking.objects.filter(traveler=self.traveler, experience=self.experience).exists())

    def test_booking_creation_rejects_blocked_date(self):
        target_date = self._booking_date()
        AvailabilityBlock.objects.create(availability=self.availability, date=target_date, reason="Descanso")

        response = self._post_create_booking(date=target_date)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fecha bloqueada")

    def test_booking_creation_rejects_range_date(self):
        target_date = self._booking_date()
        self.availability.start_date = target_date + timedelta(days=1)
        self.availability.save(update_fields=["start_date"])

        response = self._post_create_booking(date=target_date)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rango")

    def test_accept_booking_creates_invoice_conversation_and_email(self):
        booking = self._create_booking(adults=2, children=1, infants=0)

        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:accept", args=[booking.pk]),
            data={
                "pickup_time": "09:30",
                "meeting_point": "Plaza",
                "guide_response": "Te espero allí",
            },
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACCEPTED)
        self.assertIsNotNone(booking.responded_at)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[-1].to, [self.traveler.email])

        invoice = booking.invoice
        self.assertEqual(invoice.status, Invoice.Status.ISSUED)
        self.assertEqual(invoice.booking_id, booking.pk)

        conversation = booking.conversation
        self.assertEqual(conversation.status, Conversation.STATUS_ACTIVE)
        participants = list(conversation.participants.order_by("user__username"))
        self.assertEqual(len(participants), 2)
        self.assertEqual({p.user_id for p in participants}, {self.traveler.pk, self.guide.pk})

    def test_invoice_creation_is_idempotent(self):
        booking = self._create_accepted_booking(adults=2, children=1)

        first = create_invoice_from_booking(booking)
        second = create_invoice_from_booking(booking)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Invoice.objects.filter(booking=booking).count(), 1)

    def test_reject_booking_does_not_create_invoice_or_conversation(self):
        booking = self._create_booking(adults=2, children=0, infants=0)

        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:reject", args=[booking.pk]),
            data={"guide_response": "No disponibilidad"},
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.REJECTED)
        self.assertFalse(Invoice.objects.filter(booking=booking).exists())
        self.assertFalse(Conversation.objects.filter(booking=booking).exists())
        self.assertEqual(len(mail.outbox), 2)

    def test_accept_decision_screen_shows_traveler_notes(self):
        notes_text = "Tengo una lesión leve de rodilla.\n¿La ruta es muy exigente?"
        booking = self._create_booking(notes=notes_text)

        self.client.force_login(self.guide)
        response = self.client.get(reverse("bookings:accept", args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comentarios del viajero")
        self.assertContains(response, "lesión leve de rodilla")

    def test_reject_decision_screen_shows_traveler_notes(self):
        notes_text = "Soy alérgico a los frutos secos"
        booking = self._create_booking(notes=notes_text)

        self.client.force_login(self.guide)
        response = self.client.get(reverse("bookings:reject", args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comentarios del viajero")
        self.assertContains(response, "Soy alérgico a los frutos secos")

    def test_decision_screen_hides_notes_block_when_empty(self):
        booking = self._create_booking(notes="")

        self.client.force_login(self.guide)
        response = self.client.get(reverse("bookings:accept", args=[booking.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Comentarios del viajero")

    def test_decision_screen_does_not_alter_stored_notes(self):
        notes_text = "No cambiar este texto, por favor."
        booking = self._create_booking(notes=notes_text)

        self.client.force_login(self.guide)
        self.client.get(reverse("bookings:accept", args=[booking.pk]))
        self.client.get(reverse("bookings:reject", args=[booking.pk]))

        booking.refresh_from_db()
        self.assertEqual(booking.notes, notes_text)

    def test_other_guide_cannot_view_decision_screen(self):
        booking = self._create_booking(notes="Información privada del viajero")
        other_guide = User.objects.create_user(username="other-guide", password="pw", role=User.Role.GUIDE)
        other_guide.guide_profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
        other_guide.guide_profile.save(update_fields=["verification_status"])

        self.client.force_login(other_guide)
        accept_response = self.client.get(reverse("bookings:accept", args=[booking.pk]))
        reject_response = self.client.get(reverse("bookings:reject", args=[booking.pk]))

        self.assertEqual(accept_response.status_code, 404)
        self.assertEqual(reject_response.status_code, 404)

    def test_pending_booking_stores_pickup_notes_and_leaves_meeting_point_empty(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.assertEqual(booking.pickup_notes, "H10 Rubicón Palace")
        self.assertEqual(booking.meeting_point, "")

    def test_decision_screen_shows_pickup_notes_as_traveler_reference_not_meeting_point(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.client.force_login(self.guide)
        response = self.client.get(reverse("bookings:accept", args=[booking.pk]))
        content = response.content.decode()

        self.assertContains(response, "Ubicación / referencia del viajero")
        self.assertContains(response, "H10 Rubicón Palace")
        # The traveler's pickup_notes must not be presented as the (guide-defined) meeting point.
        self.assertNotIn('<p class="p-micro">📍 Punto de encuentro</p>', content)

    def test_guide_meeting_point_field_is_not_prefilled_with_pickup_notes(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.client.force_login(self.guide)
        response = self.client.get(reverse("bookings:accept", args=[booking.pk]))

        self.assertEqual(response.context["form"]["meeting_point"].value(), "")

    def test_accept_with_meeting_point_keeps_pickup_notes_and_stores_meeting_point_separately(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.client.force_login(self.guide)
        response = self.client.post(
            reverse("bookings:accept", args=[booking.pk]),
            data={
                "pickup_time": "09:00",
                "meeting_point": "Parking de Montaña Roja",
                "guide_response": "Nos vemos allí",
            },
        )

        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.pickup_notes, "H10 Rubicón Palace")
        self.assertEqual(booking.meeting_point, "Parking de Montaña Roja")

    def test_accept_booking_email_uses_meeting_point_not_pickup_notes(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.client.force_login(self.guide)
        with patch("apps.bookings.views.send_booking_status_email") as mocked_send:
            response = self.client.post(
                reverse("bookings:accept", args=[booking.pk]),
                data={
                    "pickup_time": "09:00",
                    "meeting_point": "Parking de Montaña Roja",
                    "guide_response": "Nos vemos allí",
                },
            )

        self.assertEqual(response.status_code, 302)
        mocked_send.assert_called_once()
        body = mocked_send.call_args.kwargs["message"]
        self.assertIn("Punto de encuentro: Parking de Montaña Roja", body)
        self.assertNotIn("Punto de encuentro: H10 Rubicón Palace", body)

    def test_reject_booking_email_never_uses_pickup_notes_as_meeting_point_fallback(self):
        booking = self._create_booking(pickup_notes="H10 Rubicón Palace")

        self.client.force_login(self.guide)
        with patch("apps.bookings.views.send_booking_status_email") as mocked_send:
            response = self.client.post(
                reverse("bookings:reject", args=[booking.pk]),
                data={"guide_response": "No disponibilidad"},
            )

        self.assertEqual(response.status_code, 302)
        mocked_send.assert_called_once()
        body = mocked_send.call_args.kwargs["message"]
        self.assertNotIn("Punto de encuentro: H10 Rubicón Palace", body)

    def test_booking_detail_distinguishes_pickup_notes_from_meeting_point(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        booking.pickup_notes = "H10 Rubicón Palace"
        booking.meeting_point = "Parking de Montaña Roja"
        booking.save(update_fields=["pickup_notes", "meeting_point"])

        self.client.force_login(self.traveler)
        response = self.client.get(reverse("bookings:detail", args=[booking.pk]))

        self.assertContains(response, "Tu ubicación / referencia")
        self.assertContains(response, "H10 Rubicón Palace")
        self.assertContains(response, "Parking de Montaña Roja")

    def test_change_request_form_does_not_mix_pickup_notes_and_meeting_point(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        original_meeting_point = booking.meeting_point

        booking = self._request_change(booking, adults=1)

        # A date-changing request clears meeting_point (pending re-confirmation), but never
        # copies pickup_notes into it.
        self.assertNotEqual(booking.meeting_point, booking.pickup_notes)
        self.assertIn(booking.meeting_point, ("", original_meeting_point))

    def test_change_request_stores_extras_and_pending_state(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        booking = self._request_change(booking, adults=1)

        self.assertEqual(booking.status, Booking.Status.CHANGE_REQUESTED)
        self.assertEqual(booking.extras["pre_change_status"], Booking.Status.ACCEPTED)
        self.assertIn("change_request", booking.extras)
        self.assertEqual(booking.extras["change_request"]["adults"], 1)

    def test_change_reject_restores_previous_status_and_sets_free_cancel_override(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        booking = self._request_change(booking, adults=1)

        _, booking = self._reject_change(booking)

        self.assertEqual(booking.status, Booking.Status.ACCEPTED)
        self.assertNotIn("change_request", booking.extras)
        self.assertNotIn("pre_change_status", booking.extras)
        self.assertEqual(booking.extras["free_cancel_override"]["reason"], "change_rejected")

    def test_change_accept_updates_booking_values_and_people(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        booking = self._request_change(booking, adults=1)

        _, booking = self._accept_change(booking)

        self.assertEqual(booking.status, Booking.Status.ACCEPTED)
        self.assertEqual(booking.adults, 1)
        self.assertEqual(booking.people, 1)
        self.assertEqual(booking.total_price, Decimal("40.00"))
        self.assertNotIn("change_request", booking.extras)
        self.assertNotIn("pre_change_status", booking.extras)

    @expectedFailure
    def test_known_bug_accepted_change_leaves_booking_and_invoice_totals_divergent(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        original_invoice = booking.invoice
        booking = self._request_change(booking, adults=1)

        _, booking = self._accept_change(booking)

        self.assertEqual(booking.total_price, original_invoice.total)

    @expectedFailure
    def test_known_bug_change_request_uses_stale_people_for_capacity_check(self):
        target_date = self._booking_date()
        self.availability.daily_capacity_people = 4
        self.availability.save(update_fields=["daily_capacity_people"])

        booking = self._create_accepted_booking(adults=2, children=0, date=target_date)

        booking = self._request_change(booking, adults=4)
        Booking.objects.create(
            experience=self.experience,
            traveler=self.other_traveler,
            preferred_language=self.lang_es,
            date=target_date,
            adults=1,
            children=0,
            infants=0,
            status=Booking.Status.ACCEPTED,
            pickup_time=datetime.strptime("10:00", "%H:%M").time(),
            meeting_point="Plaza",
            transport_mode=Booking.TransportMode.BICYCLE,
            pickup_notes="Punto",
            unit_price="40.00",
            total_price="40.00",
        )
        _, booking = self._accept_change(booking)

        self.assertEqual(booking.status, Booking.Status.CHANGE_REQUESTED)

    def test_free_cancel_cancels_and_rectifies_an_issued_invoice(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        create_invoice_from_booking(booking)

        booking = self._request_cancel(booking)

        self.assertEqual(booking.status, Booking.Status.CANCELED)
        self.assertTrue(Invoice.objects.filter(booking=booking).exists())
        self.assertTrue(
            Invoice.objects.filter(kind=Invoice.Kind.RECTIFICATIVE, rectifies__booking=booking).exists()
        )

    def test_cancel_request_sets_pending_state_and_extras(self):
        target = timezone.localdate() + timedelta(days=1)
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.lang_es,
            date=target,
            adults=2,
            children=0,
            infants=0,
            status=Booking.Status.ACCEPTED,
            pickup_time=datetime.strptime("10:00", "%H:%M").time(),
            meeting_point="Plaza",
            transport_mode=Booking.TransportMode.BICYCLE,
            pickup_notes="Punto",
            unit_price="40.00",
            total_price="80.00",
        )

        booking = self._request_cancel(booking)

        self.assertEqual(booking.status, Booking.Status.CANCEL_REQUESTED)
        self.assertEqual(booking.extras["pre_cancel_status"], Booking.Status.ACCEPTED)
        self.assertEqual(booking.extras["cancel_request"]["reason"], "Cambio de planes")

    def test_cancel_request_accepted_cancels_current_booking(self):
        target = timezone.localdate() + timedelta(days=1)
        booking = Booking.objects.create(
            experience=self.experience,
            traveler=self.traveler,
            preferred_language=self.lang_es,
            date=target,
            adults=2,
            children=0,
            infants=0,
            status=Booking.Status.ACCEPTED,
            pickup_time=datetime.strptime("10:00", "%H:%M").time(),
            meeting_point="Plaza",
            transport_mode=Booking.TransportMode.BICYCLE,
            pickup_notes="Punto",
            unit_price="40.00",
            total_price="80.00",
        )

        booking = self._request_cancel(booking)
        booking = self._decide_cancel(booking, "accept")

        self.assertEqual(booking.status, Booking.Status.CANCELED)
        self.assertNotIn("cancel_request", booking.extras)
        self.assertNotIn("pre_cancel_status", booking.extras)

    @expectedFailure
    def test_known_bug_rejecting_cancel_request_creates_rectification_while_booking_stays_active(self):
        booking = self._create_accepted_booking(adults=2, children=0)
        create_invoice_from_booking(booking)
        booking = self._request_cancel(booking)

        booking = self._decide_cancel(booking, "reject")

        self.assertFalse(
            Invoice.objects.filter(kind=Invoice.Kind.RECTIFICATIVE, rectifies__booking=booking).exists()
        )
