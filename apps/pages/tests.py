from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import resolve, reverse
from django.utils import translation


class SetLanguagePrelaunchFlowTests(TestCase):
	def _post_set_language(self, *, language: str, next_url: str):
		return self.client.post(
			reverse("set_language"),
			{"language": language, "next": next_url},
			follow=True,
		)

	def _assert_language_cookie(self, expected_language: str):
		self.assertEqual(
			self.client.cookies.get(settings.LANGUAGE_COOKIE_NAME).value,
			expected_language,
		)

	@override_settings(PRELAUNCH_MODE=True)
	def test_set_language_with_allowed_next_redirects_to_home_without_loop(self):
		response = self._post_set_language(language="en", next_url=reverse("pages:home"))

		with translation.override("en"):
			expected_home = reverse("pages:home")

		# Final URL should be landing in selected language.
		self.assertEqual(response.wsgi_request.path, expected_home)
		self.assertEqual(response.status_code, 200)

		# No redirect loop: one redirect from set_language is enough here.
		self.assertGreaterEqual(len(response.redirect_chain), 1)
		self.assertLess(len(response.redirect_chain), 6)

		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:home")
		self._assert_language_cookie("en")

	@override_settings(PRELAUNCH_MODE=True)
	def test_set_language_with_blocked_next_falls_back_to_landing_without_loop(self):
		blocked_next = reverse("pages:app_home")
		response = self._post_set_language(language="en", next_url=blocked_next)

		with translation.override("en"):
			expected_home = reverse("pages:home")

		# Middleware must redirect blocked internal route to landing in selected language.
		self.assertEqual(response.wsgi_request.path, expected_home)
		self.assertEqual(response.status_code, 200)

		# Expected chain: set_language -> /en/app/ ; app/ redirect -> /en/ ; prelaunch middleware (no-op, already home)
		self.assertGreaterEqual(len(response.redirect_chain), 2)
		self.assertLess(len(response.redirect_chain), 8)

		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:home")
		self._assert_language_cookie("en")

	@override_settings(PRELAUNCH_MODE=False)
	def test_set_language_with_internal_next_keeps_normal_behavior_when_prelaunch_disabled(self):
		response = self._post_set_language(language="en", next_url="/app/")

		# With prelaunch off, /app/ still redirects to the canonical home.
		with translation.override("en"):
			expected_home = reverse("pages:home")

		self.assertEqual(response.wsgi_request.path, expected_home)
		self.assertEqual(response.status_code, 200)

		self.assertGreaterEqual(len(response.redirect_chain), 2)
		self.assertLess(len(response.redirect_chain), 6)

		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:home")
		self._assert_language_cookie("en")


class PrelaunchLegalAccessTests(TestCase):
	@override_settings(PRELAUNCH_MODE=True)
	def test_legal_pages_remain_public_in_prelaunch(self):
		allowed_routes = (
			reverse("pages:privacy_policy"),
			reverse("pages:terms_and_conditions"),
			reverse("pages:cookie_policy"),
		)

		for route in allowed_routes:
			with self.subTest(route=route):
				response = self.client.get(route)
				self.assertEqual(response.status_code, 200)

	@override_settings(PRELAUNCH_MODE=True)
	def test_internal_app_route_is_still_blocked_in_prelaunch(self):
		response = self.client.get(reverse("pages:app_home"), follow=True)

		self.assertEqual(response.status_code, 200)
		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:home")

	@override_settings(PRELAUNCH_MODE=True)
	def test_root_home_is_landing_in_prelaunch(self):
		response = self.client.get(reverse("pages:home"))

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "pages/landing/landing.html")


class HomeNearMeCtaTests(TestCase):
	@override_settings(PRELAUNCH_MODE=False)
	def test_home_contains_near_me_cta_targeting_experiences_list(self):
		response = self.client.get(reverse("pages:home"))

		self.assertEqual(response.status_code, 200)
		self.assertTemplateUsed(response, "pages/home.html")
		self.assertContains(response, "data-near-me-trigger")
		self.assertContains(response, reverse("experiences:list"))

	@override_settings(PRELAUNCH_MODE=False)
	def test_app_url_redirects_to_canonical_home(self):
		response = self.client.get(reverse("pages:app_home"))

		self.assertRedirects(response, reverse("pages:home"))


@override_settings(PRELAUNCH_MODE=False)
class BookingBadgeVisualConsistencyTests(TestCase):
	"""Reservas unseen-count badge must render as `c-nav__badge` everywhere (navbar + sidebar)."""

	@classmethod
	def setUpTestData(cls):
		from apps.accounts.models import User
		from apps.experiences.models import Category, Experience
		from core.models import Language

		cls.language = Language.objects.create(code="es", name="Español")
		cls.guide = User.objects.create_user(username="guide-badge", password="pw", role=User.Role.GUIDE)
		cls.traveler = User.objects.create_user(username="traveler-badge", password="pw", role=User.Role.TRAVELER)
		category = Category.objects.create(name="Badge", slug="badge-cat")
		cls.experience = Experience.objects.create(
			guide=cls.guide,
			category=category,
			title="Badge experience",
			description="Desc",
			price="10.00",
			duration_minutes=60,
			location="Lugar",
			country="España",
			island="Lanzarote",
			city="Teguise",
			transport_requirement=Experience.TransportRequirement.BICYCLE,
			difficulty=Experience.Difficulty.EASY,
		)

	def _create_unseen_bookings(self, count):
		from datetime import time

		from django.utils import timezone

		from apps.bookings.models import Booking

		bookings = []
		for i in range(count):
			bookings.append(
				Booking(
					experience=self.experience,
					traveler=self.traveler,
					date=timezone.now().date(),
					pickup_time=time(10, 0),
					adults=1,
					children=0,
					infants=0,
					total_price="10.00",
					status=Booking.Status.PENDING,
					seen_by_guide=False,
					seen_by_traveler=False,
					preferred_language=self.language,
				)
			)
		Booking.objects.bulk_create(bookings)

	def test_no_badge_when_zero_unseen_bookings_guide(self):
		self.client.force_login(self.guide)
		response = self.client.get(reverse("pages:guide_dashboard"))

		self.assertNotContains(response, "c-nav__badge")

	def test_badge_shows_singular_count_for_guide(self):
		self._create_unseen_bookings(1)
		self.client.force_login(self.guide)
		response = self.client.get(reverse("pages:guide_dashboard"))

		self.assertContains(response, '<span class="c-nav__badge">1</span>')

	def test_badge_shows_multiple_count_for_guide(self):
		self._create_unseen_bookings(3)
		self.client.force_login(self.guide)
		response = self.client.get(reverse("pages:guide_dashboard"))

		self.assertContains(response, '<span class="c-nav__badge">3</span>')

	def test_no_badge_when_zero_unseen_bookings_traveler(self):
		self.client.force_login(self.traveler)
		response = self.client.get(reverse("pages:traveler_dashboard"))

		self.assertNotContains(response, "c-nav__badge")

	def test_badge_shows_count_for_traveler(self):
		self._create_unseen_bookings(2)
		self.client.force_login(self.traveler)
		response = self.client.get(reverse("pages:traveler_dashboard"))

		self.assertContains(response, '<span class="c-nav__badge">2</span>')

	def test_navbar_and_sidebar_use_same_badge_style(self):
		self._create_unseen_bookings(1)
		self.client.force_login(self.guide)
		response = self.client.get(reverse("pages:guide_dashboard"))
		content = response.content.decode()

		# Navbar top button + dashboard sidebar (mobile + desktop) must all use c-nav__badge.
		self.assertNotIn("notification-badge\">1<", content)
		self.assertGreaterEqual(content.count('<span class="c-nav__badge">1</span>'), 2)

