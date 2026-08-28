from datetime import datetime, timedelta
from unittest import expectedFailure

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking
from apps.experiences.models import Category, Experience
from apps.reviews.models import Review
from apps.reviews.services import traveler_can_review
from apps.profiles.models import GuideProfile
from core.models import Language


class ReviewWorkflowTests(TestCase):
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

    @expectedFailure
    def test_known_bug_future_accepted_booking_is_reviewable_before_experience_happens(self):
        booking = self._accepted_booking(date=timezone.localdate() + timedelta(days=5))

        self.assertFalse(traveler_can_review(traveler=self.traveler, experience=self.experience))
        self.assertEqual(booking.status, Booking.Status.ACCEPTED)

    def test_review_creation_auto_publishes_normal_comment_currently(self):
        booking = self._accepted_booking()
        self.client.force_login(self.traveler)

        response = self.client.post(
            reverse("reviews:create", args=[self.experience.pk]),
            data={"rating": 5, "comment": "Una experiencia increíble"},
        )

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(experience=self.experience, traveler=self.traveler)
        self.assertEqual(review.status, Review.Status.PUBLISHED)
        self.assertEqual(review.booking_id, booking.pk)

    def test_review_creation_flags_spam_comment(self):
        self._accepted_booking()
        self.client.force_login(self.traveler)

        response = self.client.post(
            reverse("reviews:create", args=[self.experience.pk]),
            data={"rating": 5, "comment": "Viagra casino promo"},
        )

        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(experience=self.experience, traveler=self.traveler)
        self.assertEqual(review.status, Review.Status.FLAGGED)
        self.assertEqual(review.flagged_reason, "Posible spam")

    def test_unique_review_per_experience_and_traveler(self):
        self._accepted_booking()
        self.client.force_login(self.traveler)

        first = self.client.post(
            reverse("reviews:create", args=[self.experience.pk]),
            data={"rating": 4, "comment": "Buen plan"},
        )
        second = self.client.post(
            reverse("reviews:create", args=[self.experience.pk]),
            data={"rating": 5, "comment": "No debería crear otra"},
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(Review.objects.filter(experience=self.experience, traveler=self.traveler).count(), 1)
