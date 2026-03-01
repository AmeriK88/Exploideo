from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import set_language
from core.views.sitemap import sitemap_xml
from django.views.generic import TemplateView



urlpatterns = [
    path("i18n/setlang/", set_language, name="set_language"),
    path("sitemap.xml", sitemap_xml, name="sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
]

urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("apps.pages.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("experiences/", include("apps.experiences.urls")),
    path("", include("apps.profiles.urls")),
    path("bookings/", include("apps.bookings.urls")),
    path("availability/", include("apps.availability.urls")),
    path("reviews/", include("apps.reviews.urls")),
    path("help/", include("apps.helpdesk.urls")),
    path("billing/", include("apps.billing.urls", namespace="billing")),
    path("messages/", include("apps.messages.urls", namespace="messages")),
)



if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

