from datetime import date as date_type
from django.db.models import Sum

from apps.bookings.models import Booking
from apps.experiences.models import Experience
from .models import ExperienceAvailability, AvailabilityBlock


def is_date_available(
    experience: Experience,
    date: date_type,
    people: int,
    *,
    exclude_booking_id: int | None = None,
) -> tuple[bool, str]:

    if not experience.is_active:
        return False, "Esta experiencia no está activa."

    if people <= 0:
        return False, "El número de personas no es válido."

    try:
        availability = ExperienceAvailability.objects.get(experience=experience)
    except ExperienceAvailability.DoesNotExist:
        # MVP: si no hay reglas, permitimos reservar
        return True, "OK"

    # Límite por excursión (por reserva) - viene de Availability
    max_per_booking = availability.max_people_per_booking
    if max_per_booking is not None and people > max_per_booking:
        return False, f"Máximo por excursión: {max_per_booking} personas."

    if not availability.is_enabled:
        return False, "Esta experiencia no acepta reservas ahora mismo."

    if availability.start_date and date < availability.start_date:
        return False, "Fecha no disponible (antes del rango permitido)."

    if availability.end_date and date > availability.end_date:
        return False, "Fecha no disponible (después del rango permitido)."

    if availability.weekdays and date.weekday() not in availability.weekdays:
        return False, "Fecha no disponible (día de la semana no permitido)."

    if AvailabilityBlock.objects.filter(availability=availability, date=date).exists():
        return False, "Fecha bloqueada por el guía."

    qs = Booking.objects.filter(
        experience=experience,
        date=date,
        status=Booking.Status.ACCEPTED,
    )

    if exclude_booking_id is not None:
        qs = qs.exclude(id=exclude_booking_id)

    if availability.daily_capacity_bookings is not None:
        used_bookings = qs.count()
        if used_bookings + 1 > availability.daily_capacity_bookings:
            return False, "No hay más cupo de excursiones para ese día."

    if availability.daily_capacity_people is not None:
        used_people = qs.aggregate(total=Sum("people"))["total"] or 0
        if used_people + people > availability.daily_capacity_people:
            return False, "No hay capacidad disponible para ese día."

    return True, "OK"