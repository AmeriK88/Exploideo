from django.contrib import admin
from .models import NewsletterSubscriber

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "source", "created_at")
    search_fields = ("email",)
    list_filter = ("source", "created_at")
