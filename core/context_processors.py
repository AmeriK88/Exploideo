from django.db.models import Q
from apps.bookings.models import Booking
from apps.messages.models import Participant


def booking_badges(request):
    if not request.user.is_authenticated:
        return {}

    data = {
        "unseen_traveler_bookings": 0,
        "unseen_guide_bookings": 0,
        "unread_messages_count": 0, 
    }

    user = request.user

    # --------------------------------
    # RESERVAS NO VISTAS
    # --------------------------------
    if hasattr(user, "is_traveler") and user.is_traveler():
        data["unseen_traveler_bookings"] = Booking.objects.filter(
            traveler=user,
            seen_by_traveler=False,
        ).count()

    if hasattr(user, "is_guide") and user.is_guide():
        data["unseen_guide_bookings"] = Booking.objects.filter(
            experience__guide=user,
            seen_by_guide=False,
        ).count()

    # --------------------------------
    # MENSAJES NO LEÍDOS
    # --------------------------------
    participants = Participant.objects.select_related("conversation").filter(
        user=user,
        conversation__status="active",
    )

    unread_total = 0

    for p in participants:
        unread_total += p.unread_count()

    data["unread_messages_count"] = unread_total

    return data