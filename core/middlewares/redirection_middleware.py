from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.urls import NoReverseMatch, Resolver404, resolve, reverse
from django.utils import translation

class CanonicalHostMiddleware:
    """
    Redirect any non-canonical host to CANONICAL_HOST, preserving path + query.
    Only active when CANONICAL_HOST is set (usually prod).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical_host = getattr(settings, "CANONICAL_HOST", None)

    def __call__(self, request):
        if not self.canonical_host:
            return self.get_response(request)

        # request.get_host() can include port
        current_host = request.get_host()
        canonical_host = self.canonical_host

        # Normalize by removing port for comparison (canonical_host should not include port)
        current_host_no_port = current_host.split(":")[0]

        if current_host_no_port == canonical_host:
            return self.get_response(request)

        # Keep path + querystring exactly as requested
        path = request.get_full_path()  # includes querystring
        scheme = "https" if request.is_secure() else "http"
        new_url = f"{scheme}://{canonical_host}{path}"

        return HttpResponsePermanentRedirect(new_url)


class PrelaunchAccessMiddleware:
    """
    When PRELAUNCH_MODE is enabled, block internal routes and keep only
    landing/legal/newsletter endpoints publicly accessible.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        self.allowed_url_names = {
            "set_language",
            "pages:home",
            "home",
            "pages:newsletter_subscribe",
            "newsletter_subscribe",
            "pages:cookie_policy",
            "cookie_policy",
            "pages:privacy_policy",
            "privacy_policy",
            "pages:terms_and_conditions",
            "terms_and_conditions",
        }

        self.allowed_namespaces = {"admin"}

        static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
        media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"
        self.allowed_prefixes = {
            "/admin/",
            "/i18n/setlang/",
            static_url if static_url.startswith("/") else f"/{static_url}",
            media_url if media_url.startswith("/") else f"/{media_url}",
        }

    def __call__(self, request):
        if not getattr(settings, "PRELAUNCH_MODE", False):
            return self.get_response(request)

        path = request.path_info or request.path
        if self._is_allowed_by_prefix(path):
            return self.get_response(request)

        match = self._resolve(path)
        if match and self._is_allowed_match(match):
            return self.get_response(request)

        target = self._home_url_for_request(request)
        if target == path:
            return self.get_response(request)

        return HttpResponseRedirect(target)

    def _resolve(self, path):
        try:
            return resolve(path)
        except Resolver404:
            return None

    def _is_allowed_by_prefix(self, path):
        for prefix in self.allowed_prefixes:
            if prefix and path.startswith(prefix):
                return True
        return False

    def _is_allowed_match(self, match):
        if match.namespace in self.allowed_namespaces:
            return True

        # Depending on how include()/i18n resolution is represented,
        # Django may expose namespaced or bare names.
        candidates = {
            match.view_name,
            match.url_name,
        }
        if match.app_name and match.url_name:
            candidates.add(f"{match.app_name}:{match.url_name}")

        return any(name in self.allowed_url_names for name in candidates if name)

    def _home_url_for_request(self, request):
        path = request.path_info or request.path
        languages = {code for code, _ in getattr(settings, "LANGUAGES", [])}
        parts = [part for part in path.split("/") if part]

        language = None
        if parts and parts[0] in languages:
            language = parts[0]
        elif getattr(request, "LANGUAGE_CODE", None) in languages:
            language = request.LANGUAGE_CODE

        return self._default_home_url(language=language)

    def _default_home_url(self, language=None):
        lang = language or getattr(settings, "LANGUAGE_CODE", "es")
        with translation.override(lang):
            try:
                return reverse("pages:home")
            except NoReverseMatch:
                return f"/{lang}/"