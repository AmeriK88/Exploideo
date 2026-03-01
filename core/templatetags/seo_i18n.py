from django import template
from django.conf import settings
from django.urls import translate_url as dj_translate_url

register = template.Library()

@register.simple_tag(takes_context=True)
def translate_url(context, lang_code: str) -> str:
    request = context.get("request")
    if not request:
        return "/"
    translated_path = dj_translate_url(request.get_full_path(), lang_code)
    return request.build_absolute_uri(translated_path)

@register.simple_tag(takes_context=True)
def canonical_url(context) -> str:
    """
    Canonical absolute URL:
    - Prod: uses settings.CANONICAL_HOST and https
    - Dev: uses request scheme/host
    - Removes query params by using request.path
    """
    request = context.get("request")
    if not request:
        return "/"

    path = request.path  # no querystring
    canonical_host = getattr(settings, "CANONICAL_HOST", None)

    if canonical_host:
        scheme = "https"
        return f"{scheme}://{canonical_host}{path}"

    # dev/local
    return request.build_absolute_uri(path)