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

		# Expected chain: set_language -> /en/app/ ; prelaunch middleware -> /en/
		self.assertGreaterEqual(len(response.redirect_chain), 2)
		self.assertLess(len(response.redirect_chain), 8)

		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:home")
		self._assert_language_cookie("en")

	@override_settings(PRELAUNCH_MODE=False)
	def test_set_language_with_internal_next_keeps_normal_behavior_when_prelaunch_disabled(self):
		response = self._post_set_language(language="en", next_url=reverse("pages:app_home"))

		# With prelaunch off, redirect should land on translated internal page.
		self.assertEqual(response.wsgi_request.path, "/en/app/")
		self.assertEqual(response.status_code, 200)

		self.assertGreaterEqual(len(response.redirect_chain), 1)
		self.assertLess(len(response.redirect_chain), 6)

		match = resolve(response.wsgi_request.path)
		self.assertEqual(f"{match.app_name}:{match.url_name}", "pages:app_home")
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


class HomeNearMeCtaTests(TestCase):
	@override_settings(PRELAUNCH_MODE=False)
	def test_app_home_contains_near_me_cta_targeting_experiences_list(self):
		response = self.client.get(reverse("pages:app_home"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "data-near-me-trigger")
		self.assertContains(response, reverse("experiences:list"))
