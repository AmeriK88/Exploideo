from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostMiddleware:
    """
    Redirige cualquier host distinto al dominio principal
    hacia el dominio canónico manteniendo path y querystring.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.canonical_host = getattr(settings, "CANONICAL_HOST", None)

    def __call__(self, request):
        if not self.canonical_host:
            return self.get_response(request)

        current_host = request.get_host()

        # Si ya estamos en el host correcto → no hacer nada
        if current_host == self.canonical_host:
            return self.get_response(request)

        # Construimos nueva URL manteniendo todo
        new_url = request.build_absolute_uri().replace(
            current_host,
            self.canonical_host
        )

        return HttpResponsePermanentRedirect(new_url)
