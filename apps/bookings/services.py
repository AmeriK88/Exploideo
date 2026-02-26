from django.utils import timezone

from apps.billing.models import Invoice
from apps.billing.services_rectification import create_rectificative_for_invoice

from django.core.exceptions import ValidationError

from django.db.models import Count, F
from apps.messages.models import Conversation, Participant, Message


def rectificate_booking_invoice_if_needed(booking, reason: str) -> None:
    """
    Genera factura rectificativa si:
    - existe factura
    - está emitida
    - NO ha sido rectificada antes

    Es idempotente y deja rastro en booking.extras (auditoría).
    """
    try:
        inv = booking.invoice
    except Invoice.DoesNotExist:
        return

    if inv.status != Invoice.Status.ISSUED:
        return

    booking.extras = booking.extras or {}
    billing = booking.extras.get("billing") or {}

    if billing.get("rectified") is True:
        return

    rect = create_rectificative_for_invoice(inv, reason=reason)

    booking.extras["billing"] = {
        "rectified": True,
        "at": timezone.now().isoformat(),
        "invoice_number": inv.number,
        "rectificative_number": rect.number,
        "reason": reason,
    }

    booking.save(update_fields=["extras", "updated_at"])
    

def validate_minors_policy(experience, adults: int, children: int, infants: int):
    minors = (children or 0) + (infants or 0)

    # HARD: NO minors
    if experience.difficulty == "hard" and minors > 0:
        raise ValidationError("Esta experiencia es DIFÍCIL y no permite menores.")

    # MOMODERATE: minors OK with an adult
    if experience.difficulty == "moderate" and minors > 0 and (adults or 0) <= 0:
        raise ValidationError("Los menores solo pueden asistir acompañados de al menos 1 adulto.")
    
def attach_chat_unread_counts(bookings, user) -> None:
    """
    Añade atributo dinámico `chat_unread` a cada booking.
    Lo calcula en pocas queries para evitar N+1.
    """
    booking_ids = [b.id for b in bookings]
    if not booking_ids:
        return

    convs = Conversation.objects.filter(booking_id__in=booking_ids).only("id", "booking_id")
    conv_id_by_booking_id = {c.booking.pk: c.pk for c in convs}
    conv_ids = list(conv_id_by_booking_id.values())

    # Default
    unread_by_conversation = {cid: 0 for cid in conv_ids}

    # last_read_at por conversación para este user
    participants = Participant.objects.filter(
        user=user,
        conversation_id__in=conv_ids,
    ).values("conversation_id", "last_read_at")

    last_read_by_conversation = {p["conversation_id"]: p["last_read_at"] for p in participants}

    # 1) last_read_at IS NULL -> unread = todos los mensajes de otros
    conv_ids_null = [cid for cid, lr in last_read_by_conversation.items() if lr is None]
    if conv_ids_null:
        rows = (
            Message.objects
            .filter(conversation_id__in=conv_ids_null)
            .exclude(sender=user)
            .values("conversation_id")
            .annotate(c=Count("id"))
        )
        for r in rows:
            unread_by_conversation[r["conversation_id"]] = r["c"]

    # 2) last_read_at NOT NULL -> mensajes de otros con created_at > last_read_at
    conv_ids_not_null = [cid for cid, lr in last_read_by_conversation.items() if lr is not None]
    if conv_ids_not_null:
        rows = (
            Message.objects
            .filter(conversation_id__in=conv_ids_not_null)
            .exclude(sender=user)
            .filter(
                conversation__participants__user=user,
                created_at__gt=F("conversation__participants__last_read_at"),
            )
            .values("conversation_id")
            .annotate(c=Count("id"))
        )
        for r in rows:
            unread_by_conversation[r["conversation_id"]] = r["c"]

    # Pegar a cada booking
    for b in bookings:
        cid = conv_id_by_booking_id.get(b.id)
        b.chat_unread = unread_by_conversation.get(cid, 0) if cid else 0