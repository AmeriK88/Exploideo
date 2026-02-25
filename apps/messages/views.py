from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bookings.models import Booking
from apps.messages.models import Conversation, Participant
from apps.messages.services import send_message, MessagingDomainError


def _assert_user_is_participant(conversation: Conversation, user):
    if not Participant.objects.filter(conversation=conversation, user=user).exists():
        raise Http404("Not found")


@login_required
def conversation_detail(request, booking_id: int):
    booking = get_object_or_404(Booking, id=booking_id)

    # Regla: chat SOLO si la booking está ACCEPTED
    if booking.status != Booking.Status.ACCEPTED:
        raise Http404("Chat not available for this booking")

    # Solo se LEE: la conversación ya debió crearse en accept_booking
    conversation = get_object_or_404(Conversation, booking=booking)

    _assert_user_is_participant(conversation, request.user)

    msgs = (
        conversation.messages # type: ignore[attr-defined]
        .select_related("sender")
        .order_by("created_at")[:200]
    )

    # Marcar leído: actualizamos last_read_at al momento actual
    Participant.objects.filter(conversation=conversation, user=request.user).update(
        last_read_at=timezone.now()
    )

    return render(
        request,
        "messages/detail.html",
        {"booking": booking, "conversation": conversation, "messages": msgs},
    )


@login_required
def send_message_view(request, booking_id: int):
    if request.method != "POST":
        raise Http404()

    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != Booking.Status.ACCEPTED:
        raise Http404("Chat not available for this booking")

    conversation = get_object_or_404(Conversation, booking=booking)

    _assert_user_is_participant(conversation, request.user)

    body = request.POST.get("body", "")

    try:
        send_message(conversation=conversation, sender=request.user, body=body)
    except MessagingDomainError:
        # Si quieres, aquí luego metemos messages.error(request, "...") y devolvemos al chat
        pass

    return redirect("messages:conversation_detail", booking_id=booking.pk) 