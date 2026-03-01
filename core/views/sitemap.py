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

# Idiomas soportados
LANGS = ["es", "en"]

# Idioma por defecto del proyecto (el que quieres como "fallback")
DEFAULT_LANG = "es"


def _abs(request, path: str) -> str:
    return request.build_absolute_uri(path)


def sitemap_xml(request):
    """
    Sitemap con alternates hreflang para ES/EN y x-default.
    Genera una entrada <url> por cada versión lingüística (recomendado).
    """
    xml_parts = []
    xml_parts.append('<?xml version="1.0" encoding="UTF-8"?>')
    xml_parts.append("<!-- EXPLOIDEO_SITEMAP_CUSTOM -->")
    xml_parts.append(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">'
    )

    for url_name in URL_NAMES:
        # 1) Construimos alternates por idioma
        alternates = {}
        for lang in LANGS:
            with translation.override(lang):
                alternates[lang] = _abs(request, reverse(url_name))

        # 2) x-default (normalmente apunta al selector de idioma o al default)
        x_default_url = alternates.get(DEFAULT_LANG, next(iter(alternates.values())))

        # 3) IMPORTANTE: una entrada <url> por cada versión (ES y EN)
        for lang in LANGS:
            loc = alternates[lang]

            xml_parts.append("<url>")
            xml_parts.append(f"<loc>{loc}</loc>")

            # alternates (incluyendo self-referential)
            for alt_lang, href in alternates.items():
                xml_parts.append(
                    f'<xhtml:link rel="alternate" hreflang="{alt_lang}" href="{href}" />'
                )

            # x-default
            xml_parts.append(
                f'<xhtml:link rel="alternate" hreflang="x-default" href="{x_default_url}" />'
            )

            xml_parts.append("<changefreq>weekly</changefreq>")
            xml_parts.append("<priority>0.8</priority>")
            xml_parts.append("</url>")

    xml_parts.append("</urlset>")
    return HttpResponse("\n".join(xml_parts), content_type="application/xml")