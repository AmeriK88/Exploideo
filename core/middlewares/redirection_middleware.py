from django.conf import settings
from django.http import HttpResponsePermanentRedirect

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