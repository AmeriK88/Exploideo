from django.contrib import admin
from .models import NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "role",
        "region",
        "island",
        "is_official_guide",
        "consent",
        "source",
        "created_at",
    )

    search_fields = ("email",)

    list_filter = (
        "role",
        "region",
        "island",
        "is_official_guide",
        "consent",
        "source",
        "created_at",
    )

    ordering = ("-created_at",)
    list_per_page = 50

    # Opcional: hace que el admin sea más cómodo de editar
    readonly_fields = ("created_at",)

    fieldsets = (
        ("Suscriptor", {"fields": ("email", "created_at", "source")}),
        ("Segmentación", {"fields": ("role", "region", "island", "is_official_guide")}),
        ("Consentimiento", {"fields": ("consent",)}),
    )
