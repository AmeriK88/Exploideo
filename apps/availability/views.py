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
    people = int(request.GET.get("people", "1"))

    if not start or not end or start > end:
        return JsonResponse({"error": "Invalid range"}, status=400)

    # 👇 EARLY CHECK: max por reserva (no depende de la fecha)
    try:
        availability = ExperienceAvailability.objects.get(experience=experience)
        max_per_booking = availability.max_people_per_booking
        if max_per_booking is not None and people > max_per_booking:
            return JsonResponse({
                "disabled": [],
                "blocked_by": "max_per_booking",
                "message": f"Máximo por reserva: {max_per_booking} personas."
            })
    except ExperienceAvailability.DoesNotExist:
        pass

    disabled = []
    cursor = start
    while cursor <= end:
        ok, _msg = is_date_available(experience, cursor, people)
        if not ok:
            disabled.append(cursor.isoformat())
        cursor = cursor.fromordinal(cursor.toordinal() + 1)

    return JsonResponse({"disabled": disabled})
