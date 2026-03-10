from unittest.mock import MagicMock, patch
import time

from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.experiences.forms import ExperienceForm
from apps.experiences.models import Category, Experience
from apps.experiences.services.geocoding import geocode_experience_location
from apps.profiles.models import GuideProfile


class GeocodingServiceTests(TestCase):
	def setUp(self):
		cache.clear()

	@patch("apps.experiences.services.geocoding.requests.get")
	def test_geocode_returns_coordinates_when_provider_has_result(self, mock_get):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		result = geocode_experience_location(experience)

		self.assertEqual(result, (29.1156, -13.5632))

	@patch("apps.experiences.services.geocoding.requests.get")
	def test_geocode_returns_none_when_provider_has_no_result(self, mock_get):
		experience = Experience(location="Lugar inexistente")

		fake_response = MagicMock()
		fake_response.json.return_value = []
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		self.assertIsNone(geocode_experience_location(experience))

	@patch("apps.experiences.services.geocoding.requests.get")
	def test_repeated_calls_reuse_cached_result_without_extra_http_calls(self, mock_get):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		first = geocode_experience_location(experience)
		second = geocode_experience_location(experience)

		self.assertEqual(first, (29.1156, -13.5632))
		self.assertEqual(second, (29.1156, -13.5632))
		self.assertEqual(mock_get.call_count, 1)

	@patch("apps.experiences.services.geocoding.cache.set")
	@patch("apps.experiences.services.geocoding.requests.get")
	def test_cache_is_written_with_expected_ttl(self, mock_get, cache_set_mock):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		result = geocode_experience_location(experience)

		self.assertEqual(result, (29.1156, -13.5632))
		cache_set_mock.assert_called_once()
		_, kwargs = cache_set_mock.call_args
		self.assertEqual(kwargs["timeout"], 86400)

	@override_settings(GEOCODING_CACHE_TTL=1)
	@patch("apps.experiences.services.geocoding.requests.get")
	def test_cache_entry_expires_after_ttl(self, mock_get):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		geocode_experience_location(experience)
		geocode_experience_location(experience)
		self.assertEqual(mock_get.call_count, 1)

		time.sleep(1.1)
		geocode_experience_location(experience)
		self.assertEqual(mock_get.call_count, 2)

	@patch("apps.experiences.services.geocoding.cache.get", side_effect=Exception("cache down"))
	@patch("apps.experiences.services.geocoding.requests.get")
	def test_geocoding_still_works_if_cache_get_unavailable(self, mock_get, _cache_get_mock):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		result = geocode_experience_location(experience)

		self.assertEqual(result, (29.1156, -13.5632))
		mock_get.assert_called_once()

	@patch("apps.experiences.services.geocoding.cache.set", side_effect=Exception("cache down"))
	@patch("apps.experiences.services.geocoding.requests.get")
	def test_geocoding_still_returns_coords_if_cache_set_unavailable(self, mock_get, _cache_set_mock):
		experience = Experience(location="Playa de Famara", city="Teguise", island="Lanzarote", country="España")

		fake_response = MagicMock()
		fake_response.json.return_value = [{"lat": "29.1156", "lon": "-13.5632"}]
		fake_response.raise_for_status.return_value = None
		mock_get.return_value = fake_response

		result = geocode_experience_location(experience)

		self.assertEqual(result, (29.1156, -13.5632))


class ExperienceGeocodingFlowTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.guide = User.objects.create_user(username="guide1", password="pass123", role=User.Role.GUIDE)
		profile, _ = GuideProfile.objects.get_or_create(user=self.guide)
		profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
		profile.save(update_fields=["verification_status"])
		self.category = Category.objects.create(name="Senderismo", slug="senderismo")
		self.client.force_login(self.guide)

	def _create_payload(self, **overrides):
		payload = {
			"category": str(self.category.pk),
			"title": "Ruta volcánica",
			"description": "Descripción completa",
			"price": "49.90",
			"duration_minutes": "180",
			"location": "Playa de Famara",
			"country": "España",
			"region": "Canarias",
			"province": "Las Palmas",
			"island": "Lanzarote",
			"city": "Teguise",
			"transport_requirement": Experience.TransportRequirement.ON_FOOT,
			"tags": "famara, volcan",
			"difficulty": Experience.Difficulty.EASY,
			"is_active": "on",
		}
		payload.update(overrides)
		return payload

	@patch("apps.experiences.views.geocode_experience_location", return_value=(29.1156, -13.5632))
	def test_create_sets_coordinates_automatically(self, geocode_mock):
		response = self.client.post(reverse("experiences:create"), data=self._create_payload())

		self.assertEqual(response.status_code, 302)
		exp = Experience.objects.get(title="Ruta volcánica")
		self.assertIsNotNone(exp.latitude)
		self.assertIsNotNone(exp.longitude)
		self.assertAlmostEqual(float(exp.latitude), 29.1156, places=4)
		self.assertAlmostEqual(float(exp.longitude), -13.5632, places=4)
		geocode_mock.assert_called_once()

	@patch("apps.experiences.views.geocode_experience_location", return_value=None)
	def test_create_still_saves_when_geocoding_fails(self, geocode_mock):
		response = self.client.post(reverse("experiences:create"), data=self._create_payload(title="Sin coordenadas"))

		self.assertEqual(response.status_code, 302)
		exp = Experience.objects.get(title="Sin coordenadas")
		self.assertIsNone(exp.latitude)
		self.assertIsNone(exp.longitude)
		geocode_mock.assert_called_once()

	@patch("apps.experiences.views.geocode_experience_location", return_value=(28.9630, -13.5477))
	def test_edit_regeocodes_when_location_fields_change(self, geocode_mock):
		exp = Experience.objects.create(
			guide=self.guide,
			category=self.category,
			title="Original",
			description="Desc",
			price="35.00",
			duration_minutes=120,
			location="Caleta",
			country="España",
			region="Canarias",
			province="Las Palmas",
			island="Lanzarote",
			city="Yaiza",
			transport_requirement=Experience.TransportRequirement.ON_FOOT,
			difficulty=Experience.Difficulty.EASY,
			latitude=10.0,
			longitude=20.0,
		)

		payload = self._create_payload(title="Original", city="Tinajo")
		response = self.client.post(reverse("experiences:edit", args=[exp.pk]), data=payload)

		self.assertEqual(response.status_code, 302)
		exp.refresh_from_db()
		self.assertEqual(exp.city, "Tinajo")
		self.assertAlmostEqual(float(exp.latitude), 28.9630, places=4)
		self.assertAlmostEqual(float(exp.longitude), -13.5477, places=4)
		geocode_mock.assert_called_once()

	@patch("apps.experiences.views.geocode_experience_location", return_value=(28.5, -13.5))
	def test_edit_does_not_regeocode_when_location_fields_do_not_change(self, geocode_mock):
		exp = Experience.objects.create(
			guide=self.guide,
			category=self.category,
			title="Sin cambios geo",
			description="Desc",
			price="35.00",
			duration_minutes=120,
			location="Caleta",
			country="España",
			region="Canarias",
			province="Las Palmas",
			island="Lanzarote",
			city="Yaiza",
			transport_requirement=Experience.TransportRequirement.ON_FOOT,
			difficulty=Experience.Difficulty.EASY,
			latitude=11.0,
			longitude=21.0,
		)

		payload = self._create_payload(
			title="Sin cambios geo",
			description="Desc editada",
			location="Caleta",
			country="España",
			region="Canarias",
			province="Las Palmas",
			island="Lanzarote",
			city="Yaiza",
		)
		response = self.client.post(reverse("experiences:edit", args=[exp.pk]), data=payload)

		self.assertEqual(response.status_code, 302)
		exp.refresh_from_db()
		self.assertEqual(float(exp.latitude), 11.0)
		self.assertEqual(float(exp.longitude), 21.0)
		geocode_mock.assert_not_called()


class ExperienceValidationAndFormTests(TestCase):
	def test_form_does_not_expose_manual_lat_lng_inputs(self):
		form = ExperienceForm()
		self.assertNotIn("latitude", form.fields)
		self.assertNotIn("longitude", form.fields)

	def test_model_rejects_invalid_coordinate_pairs_when_set_programmatically(self):
		guide = User.objects.create_user(username="guide2", password="pass123", role=User.Role.GUIDE)
		category = Category.objects.create(name="Kayak", slug="kayak")
		exp = Experience(
			guide=guide,
			category=category,
			title="Test",
			description="Desc",
			price="20.00",
			duration_minutes=60,
			location="Lugar",
			transport_requirement=Experience.TransportRequirement.ON_FOOT,
			difficulty=Experience.Difficulty.EASY,
			latitude=29.0,
			longitude=None,
		)

		with self.assertRaises(ValidationError):
			exp.full_clean()


class ExperienceNearMeDiscoveryTests(TestCase):
	def setUp(self):
		self.client = Client()
		self.category_hiking = Category.objects.create(name="Hiking", slug="hiking")
		self.category_boat = Category.objects.create(name="Boat", slug="boat")

		self.guide = User.objects.create_user(username="near_guide", password="pass123", role=User.Role.GUIDE)
		profile, _ = GuideProfile.objects.get_or_create(user=self.guide)
		profile.verification_status = GuideProfile.VerificationStatus.VERIFIED
		profile.save(update_fields=["verification_status"])

	def _create_experience(self, *, title, category, city="Arrecife", latitude=None, longitude=None):
		return Experience.objects.create(
			guide=self.guide,
			category=category,
			title=title,
			description="Desc",
			price="30.00",
			duration_minutes=120,
			location="Canarias",
			country="España",
			region="Canarias",
			province="Las Palmas",
			island="Lanzarote",
			city=city,
			transport_requirement=Experience.TransportRequirement.ON_FOOT,
			difficulty=Experience.Difficulty.EASY,
			is_active=True,
			latitude=latitude,
			longitude=longitude,
		)

	def test_list_without_near_me_keeps_normal_behavior(self):
		exp_a = self._create_experience(title="Normal A", category=self.category_hiking)
		exp_b = self._create_experience(title="Normal B", category=self.category_hiking)

		response = self.client.get(reverse("experiences:list"))

		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.context["near_me_active"])
		experiences = list(response.context["experiences"])
		self.assertIn(exp_a, experiences)
		self.assertIn(exp_b, experiences)

	def test_invalid_near_me_coordinates_do_not_break_listing(self):
		self._create_experience(title="Fallback item", category=self.category_hiking)

		response = self.client.get(
			reverse("experiences:list"),
			{"near_me": "1", "user_lat": "oops", "user_lng": "-13.55"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.context["near_me_active"])
		self.assertTrue(response.context["near_me_error"])

	def test_near_me_orders_by_distance(self):
		near = self._create_experience(
			title="Near",
			category=self.category_hiking,
			latitude=28.9600,
			longitude=-13.5500,
		)
		far = self._create_experience(
			title="Far",
			category=self.category_hiking,
			latitude=29.3000,
			longitude=-13.7000,
		)
		self._create_experience(title="No coords", category=self.category_hiking)

		response = self.client.get(
			reverse("experiences:list"),
			{"near_me": "1", "user_lat": "28.961", "user_lng": "-13.552"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.context["near_me_active"])
		experiences = response.context["experiences"]
		titles = [exp.title for exp in experiences]
		self.assertEqual(titles[0], near.title)
		self.assertIn(far.title, titles)

	def test_near_me_handles_missing_experience_coordinates(self):
		self._create_experience(title="With coords", category=self.category_hiking, latitude=28.95, longitude=-13.53)
		self._create_experience(title="Without coords", category=self.category_hiking)

		response = self.client.get(
			reverse("experiences:list"),
			{"near_me": "1", "user_lat": "28.96", "user_lng": "-13.55"},
		)

		self.assertEqual(response.status_code, 200)
		titles = [exp.title for exp in response.context["experiences"]]
		self.assertIn("Without coords", titles)

	def test_near_me_combines_with_existing_filters(self):
		self._create_experience(
			title="Hiking near",
			category=self.category_hiking,
			city="Arrecife",
			latitude=28.9601,
			longitude=-13.5501,
		)
		self._create_experience(
			title="Boat near",
			category=self.category_boat,
			city="Arrecife",
			latitude=28.9602,
			longitude=-13.5502,
		)

		response = self.client.get(
			reverse("experiences:list"),
			{
				"near_me": "1",
				"user_lat": "28.96",
				"user_lng": "-13.55",
				"category": self.category_hiking.slug,
				"city": "Arrecife",
			},
		)

		self.assertEqual(response.status_code, 200)
		titles = [exp.title for exp in response.context["experiences"]]
		self.assertIn("Hiking near", titles)
		self.assertNotIn("Boat near", titles)

	def test_templates_render_with_and_without_distance_values(self):
		self._create_experience(title="Has distance", category=self.category_hiking, latitude=28.9601, longitude=-13.5501)
		self._create_experience(title="No distance", category=self.category_hiking)

		near_response = self.client.get(
			reverse("experiences:list"),
			{"near_me": "1", "user_lat": "28.96", "user_lng": "-13.55"},
		)
		regular_response = self.client.get(reverse("experiences:list"))

		self.assertContains(near_response, "km de ti")
		self.assertEqual(regular_response.status_code, 200)
