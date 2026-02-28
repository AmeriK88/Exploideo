from django.http import HttpResponse
from django.urls import reverse
from django.utils import translation

URL_NAMES = [
    "pages:home",
    "helpdesk:helpdesk",
    "pages:terms_and_conditions",
    "pages:privacy_policy",
    "pages:cookie_policy",
]

LANGS = ["es", "en"]


def _abs(request, path: str) -> str:
    return request.build_absolute_uri(path)


def sitemap_xml(request):
    """
    Simple sitemap.xml con alternates hreflang (xhtml:link) para ES/EN.
    """
    url_items = []

    for url_name in URL_NAMES:
        # Generamos URL para cada idioma
        alternates = {}
        for lang in LANGS:
            with translation.override(lang):
                alternates[lang] = _abs(request, reverse(url_name))

        # Elegimos loc principal: el idioma actual o ES por defecto
        loc = alternates.get(translation.get_language() or "es", alternates["es"])

        url_items.append((loc, alternates))

    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_parts.append("<!-- EXPLOIDEO_SITEMAP_CUSTOM -->")
    xml_parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
    )

    for loc, alternates in url_items:
        xml_parts.append("<url>")
        xml_parts.append(f"<loc>{loc}</loc>")

        for lang, href in alternates.items():
            xml_parts.append(
                f'<xhtml:link rel="alternate" hreflang="{lang}" href="{href}" />'
            )

        xml_parts.append("<changefreq>weekly</changefreq>")
        xml_parts.append("<priority>0.8</priority>")
        xml_parts.append("</url>")

    xml_parts.append("</urlset>")

    return HttpResponse("\n".join(xml_parts), content_type="application/xml")