from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
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
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

