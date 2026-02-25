from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.bookings.models import Booking
from apps.messages.models import Conversation, Participant
from apps.messages.services import ensure_conversation_for_accepted_booking, send_message, MessagingDomainError


def _assert_user_is_participant(conversation: Conversation, user):
    if not Participant.objects.filter(conversation=conversation, user=user).exists():
        raise Http404("Not found")


@login_required
def conversation_detail(request, booking_id: int):
    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != Booking.Status.ACCEPTED:
        raise Http404("Chat not available for this booking")

    conversation = Conversation.objects.filter(booking=booking).first()
    if conversation is None:
        try:
            conversation = ensure_conversation_for_accepted_booking(booking)
        except MessagingDomainError:
            raise Http404("Chat not available for this booking")

    _assert_user_is_participant(conversation, request.user)

    chat_messages = (
        conversation.messages.select_related("sender") # type: ignore[attr-defined]
        .order_by("created_at")[:200]
    )

    Participant.objects.filter(conversation=conversation, user=request.user).update(
        last_read_at=timezone.now()
    )

    return render(
        request,
        "messages/detail.html",
        {
            "booking": booking,
            "conversation": conversation,
            "chat_messages": chat_messages,
        },
    )


@login_required
def send_message_view(request, booking_id: int):
    if request.method != "POST":
        raise Http404()

    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != Booking.Status.ACCEPTED:
        raise Http404("Chat not available for this booking")

    conversation = Conversation.objects.filter(booking=booking).first()
    if conversation is None:
        try:
            conversation = ensure_conversation_for_accepted_booking(booking)
        except MessagingDomainError:
            raise Http404("Chat not available for this booking")

    _assert_user_is_participant(conversation, request.user)

    body = request.POST.get("body", "")

    try:
        send_message(conversation=conversation, sender=request.user, body=body)
        # feedback opcional (texto, NO objeto)
        # django_messages.success(request, "Mensaje enviado.")
    except MessagingDomainError as e:
        django_messages.error(request, str(e))

    return redirect("messages:conversation_detail", booking_id=booking.pk)