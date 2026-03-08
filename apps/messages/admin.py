from django.contrib import admin
from .models import Conversation, Participant, Message


# =========================
# Participant Inline
# =========================

class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "last_read_at"]
    fields = (
        "user",
        "role",
        "last_read_at",
        "is_muted",
        "is_blocked",
        "created_at",
    )


# =========================
# Message Inline
# =========================

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    autocomplete_fields = ["sender"]
    readonly_fields = ["created_at"]
    fields = (
        "sender",
        "kind",
        "body",
        "created_at",
    )

    ordering = ["created_at"]

    def has_add_permission(self, request, obj=None):
        return False  # evitar crear mensajes desde admin


# =========================
# Conversation Admin
# =========================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "booking",
        "status",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "booking__id",
        "booking__traveler__username",
        "booking__guide__username",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = [
        "booking",
    ]

    inlines = [
        ParticipantInline,
        MessageInline,
    ]


# =========================
# Participant Admin
# =========================

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "conversation",
        "user",
        "role",
        "is_muted",
        "is_blocked",
        "last_read_at",
        "created_at",
    )

    list_filter = (
        "role",
        "is_muted",
        "is_blocked",
    )

    search_fields = (
        "user__username",
        "conversation__id",
    )

    autocomplete_fields = [
        "user",
        "conversation",
    ]

    readonly_fields = (
        "created_at",
        "last_read_at",
    )


# =========================
# Message Admin
# =========================

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "conversation",
        "sender",
        "kind",
        "short_body",
        "created_at",
    )

    list_filter = (
        "kind",
        "created_at",
    )

    search_fields = (
        "body",
        "sender__username",
        "conversation__id",
    )

    autocomplete_fields = [
        "conversation",
        "sender",
    ]

    readonly_fields = [
        "created_at",
    ]

    ordering = ["-created_at"]

    def short_body(self, obj):
        return obj.body[:80]

    short_body.short_description = "Message"