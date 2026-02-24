from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import guide_required
from apps.experiences.models import Experience
from .forms import ExperienceAvailabilityForm, AvailabilityBlockForm
from .models import ExperienceAvailability, AvailabilityBlock
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils.dateparse import parse_date  
from apps.availability.services import is_date_available

from django.core.exceptions import ValidationError
from apps.bookings.services import validate_minors_policy


@guide_required
def availability_manage(request, experience_id: int):
    experience = get_object_or_404(Experience, pk=experience_id, guide=request.user)

    availability, _ = ExperienceAvailability.objects.get_or_create(experience=experience)

    if request.method == "POST":
        form = ExperienceAvailabilityForm(request.POST, instance=availability)
        if form.is_valid():
            form.save()
            messages.success(request, "Disponibilidad actualizada.")
            return redirect("availability:manage", experience_id=experience.pk)
    else:
        # precargar weekdays como strings para el widget
        initial = {"weekdays": [str(x) for x in (availability.weekdays or [])]}
        form = ExperienceAvailabilityForm(instance=availability, initial=initial)

    block_form = AvailabilityBlockForm()
    # Query directa => Pylance OK
    blocks = AvailabilityBlock.objects.filter(availability=availability).order_by("date")

    return render(
        request,
        "availability/manage.html",
        {
            "experience": experience,
            "availability": availability,
            "form": form,
            "block_form": block_form,
            "blocks": blocks,
        },
    )


@guide_required
def add_block(request, experience_id: int):
    experience = get_object_or_404(Experience, pk=experience_id, guide=request.user)
    availability, _ = ExperienceAvailability.objects.get_or_create(experience=experience)

    if request.method == "POST":
        form = AvailabilityBlockForm(request.POST)
        if form.is_valid():
            block = form.save(commit=False)
            block.availability = availability
            try:
                block.save()
                messages.success(request, "Fecha bloqueada.")
            except Exception:
                messages.error(request, "Esa fecha ya estaba bloqueada.")

    return redirect("availability:manage", experience_id=experience.pk)


@guide_required
def delete_block(request, block_id: int):
    block = get_object_or_404(
        AvailabilityBlock,
        pk=block_id,
        availability__experience__guide=request.user,
    )
    experience_id = block.availability.experience.pk
    block.delete()
    messages.success(request, "Bloqueo eliminado.")
    return redirect("availability:manage", experience_id=experience_id)


@require_GET
def experience_disabled_dates(request, experience_id):
    experience = get_object_or_404(Experience, pk=experience_id, is_active=True)

    start = parse_date(request.GET.get("start"))
    end = parse_date(request.GET.get("end"))

    adults = int(request.GET.get("adults", "1"))
    children = int(request.GET.get("children", "0"))
    infants = int(request.GET.get("infants", "0"))

    people = int(request.GET.get("people", str(max(1, adults + children + infants))))

    if not start or not end or start > end:
        return JsonResponse({"error": "Invalid range"}, status=400)

    availability, _ = ExperienceAvailability.objects.get_or_create(experience=experience)
    max_per_booking = availability.max_people_per_booking

    blocked_by = None
    message = None

    # 1) Policy menores (solo mensaje, NO return)
    try:
        validate_minors_policy(experience, adults, children, infants)
    except ValidationError as e:
        blocked_by = "minors_policy"
        message = str(e)

    # 2) Max por reserva (solo mensaje, NO return)
    if max_per_booking is not None and people > max_per_booking:
        blocked_by = blocked_by or "max_per_booking"
        message = message or f"Máximo por reserva: {max_per_booking} personas."

    # 3) Para calcular disabled, usa people “clamp” si hace falta
    people_for_calc = people
    if max_per_booking is not None:
        people_for_calc = min(people_for_calc, max_per_booking)

    disabled = []
    cursor = start
    while cursor <= end:
        ok, _msg = is_date_available(experience, cursor, people_for_calc)
        if not ok:
            disabled.append(cursor.isoformat())
        cursor = cursor.fromordinal(cursor.toordinal() + 1)

    payload = {"disabled": disabled}
    if blocked_by:
        payload["blocked_by"] = blocked_by
    if message:
        payload["message"] = message

    return JsonResponse(payload)