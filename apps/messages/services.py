from django.db import transaction
from django.utils import timezone

from apps.messages.models import Conversation, Participant, Message


def _is_booking_accepted(booking) -> bool:
    from apps.bookings.models import Booking
    return booking.status == Booking.Status.ACCEPTED


class MessagingDomainError(Exception):
    pass


@transaction.atomic
def ensure_conversation_for_accepted_booking(booking) -> Conversation:
    """
    Crea (si no existe) la conversación + participantes para una booking aceptada.
    Debe llamarse desde el flujo de 'accept booking'.
    """
    # Regla de negocio: solo si está aceptada
    # Ajusta el check según tu Booking model (status/enum/choices).
    if not _is_booking_accepted(booking):
        raise MessagingDomainError("Conversation can only be created for accepted bookings")

    conversation, created = Conversation.objects.get_or_create(booking=booking)

    # Derivar participantes desde booking.
    traveler_user = booking.traveler
    guide_user = booking.experience.guide

    Participant.objects.get_or_create(
        conversation=conversation,
        user=traveler_user,
        defaults={"role": Participant.ROLE_TRAVELER},
    )
    Participant.objects.get_or_create(
        conversation=conversation,
        user=guide_user,
        defaults={"role": Participant.ROLE_GUIDE},
    )

    return conversation


@transaction.atomic
def send_message(*, conversation: Conversation, sender, body: str, kind: str = Message.KIND_TEXT) -> Message:
    """
    Envía un mensaje.
    (Permisos se validan fuera o aquí, como prefieras; yo prefiero aquí para blindaje.)
    """
    body = (body or "").strip()
    if not body:
        raise MessagingDomainError("Message body cannot be empty")

    # Permiso: sender debe ser participante
    if not Participant.objects.filter(conversation=conversation, user=sender, is_blocked=False).exists():
        raise MessagingDomainError("User is not allowed to send messages in this conversation")

    msg = Message.objects.create(
        conversation=conversation,
        sender=sender,
        body=body,
        kind=kind,
    )

    # actualizar unread simple: no hace falta; last_read_at se mueve cuando abren el chat
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])

    return msg