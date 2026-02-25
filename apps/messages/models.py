from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """
    1 conversación por reserva (booking). Se crea cuando la booking pasa a ACCEPTED.
    """
    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="conversation",
    )

    STATUS_ACTIVE = "active"
    STATUS_CLOSED = "closed"
    STATUS_BLOCKED = "blocked"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_BLOCKED, "Blocked"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Conversation(booking_id={self.booking.pk})"


class Participant(models.Model):
    """
    Participantes del chat.
    Útil para permisos, 'unread', muting, bloqueo, etc.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_participations",
    )

    ROLE_TRAVELER = "traveler"
    ROLE_GUIDE = "guide"
    ROLE_CHOICES = [
        (ROLE_TRAVELER, "Traveler"),
        (ROLE_GUIDE, "Guide"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    last_read_at = models.DateTimeField(null=True, blank=True)

    is_muted = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("conversation", "user")]
        indexes = [
            models.Index(fields=["conversation", "user"]),
            models.Index(fields=["user"]),
        ]

    def mark_read_now(self):
        self.last_read_at = timezone.now()
        self.save(update_fields=["last_read_at"])

    def __str__(self) -> str:
        return f"Participant(conversation_id={self.conversation.pk}, user_id={self.user.pk})"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )

    KIND_TEXT = "text"
    KIND_SYSTEM = "system"
    KIND_CHOICES = [
        (KIND_TEXT, "Text"),
        (KIND_SYSTEM, "System"),
    ]
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_TEXT)

    body = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message(conversation_id={self.conversation.pk}, sender_id={self.sender.pk})"