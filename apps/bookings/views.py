from decimal import Decimal
from datetime import date, datetime, timedelta, time
from django.urls import reverse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.availability.services import is_date_available
from apps.experiences.models import Experience
from core.decorators import guide_required
from .emails import send_booking_status_email
from .forms import BookingForm, BookingDecisionForm, BookingChangeRequestForm
from .models import Booking
from apps.billing.services import create_invoice_from_booking
from apps.billing.models import Invoice
from apps.bookings.services import rectificate_booking_invoice_if_needed, validate_minors_policy

from django.core.exceptions import ValidationError as CoreValidationError

from core.models import Language



def booking_start_dt_local(booking):
    """
    Devuelve un datetime (timezone-aware) con date + pickup_time.
    Si no hay pickup_time, devuelve None.
    """
    if not booking.pickup_time:
        return None
    naive = datetime.combine(booking.date, booking.pickup_time)
    return timezone.make_aware(naive, timezone.get_current_timezone())

def booking_end_dt_local(booking):
    """
    Devuelve un datetime (timezone-aware) que marca el "fin" válido de la reserva para acciones.
    Si hay pickup_time, usamos ese inicio como referencia (acción permitida hasta antes del inicio).
    Si NO hay pickup_time (casos legacy), usamos el final del día local (23:59:59).
    """
    tz = timezone.get_current_timezone()

    start_dt = booking_start_dt_local(booking)
    if start_dt is not None:
        return start_dt

    # Legacy fallback
    naive_end = datetime.combine(booking.date, time.max)
    return timezone.make_aware(naive_end, tz)


def booking_has_started(booking) -> bool:
    """
    True si ya no se permiten cambios/cancelaciones: ya empezó o la fecha ya pasó.
    """
    end_dt = booking_end_dt_local(booking)
    return timezone.now() >= end_dt


def can_cancel_free(booking) -> bool:
    """
    Reglas:
    - Nunca se puede cancelar gratis si la experiencia ya empezó / ya pasó.
    - PENDING: cancelable gratis SOLO si no ha pasado.
    - ACCEPTED:
        - gratis si faltan >= 48h (con pickup_time)
        - si no hay pickup_time (legacy), gratis SOLO si no ha pasado (no infinito)
    """

    # Guard: if has started / NO Free cxl 
    if booking_has_started(booking):
        return False

    # Override: of change rejencted - free cxl allowance
    override = (booking.extras or {}).get("free_cancel_override")
    if override and override.get("reason") == "change_rejected":
        return True

    if booking.status == Booking.Status.PENDING:
        return True

    if booking.status == Booking.Status.ACCEPTED:
        start_dt = booking_start_dt_local(booking)
        if start_dt is None:
            return True  
        return timezone.now() <= (start_dt - timedelta(hours=48))

    return False


@login_required
def create_booking(request, experience_id):
    if not request.user.is_traveler():
        messages.error(request, "Solo los viajeros pueden hacer reservas.")
        return redirect("pages:dashboard")

    experience = get_object_or_404(Experience, pk=experience_id, is_active=True)

    form = BookingForm(request.POST or None, experience=experience)

    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        booking.experience = experience
        booking.traveler = request.user

        # Transport defined by experience
        booking.transport_mode = getattr(experience, "transport_requirement", Booking.TransportMode.ON_FOOT)

        # Avoid duplicates
        duplicate_exists = Booking.objects.filter(
            traveler=request.user,
            experience=experience,
            date=booking.date,
            status=Booking.Status.PENDING,
        ).exists()

        if duplicate_exists:
            messages.warning(
                request,
                "Ya tienes una solicitud pendiente para esta experiencia en esa fecha. Revisa 'Mis reservas'."
            )
            return redirect("bookings:traveler_list")

        adults = booking.adults or 0
        children = booking.children or 0

        # SNAPSHOT
        unit_price = Decimal(str(experience.price or "0"))
        booking.unit_price = unit_price

        children_unit = unit_price * Decimal("0.5")
        booking.total_price = (unit_price * Decimal(adults)) + (children_unit * Decimal(children))

        # UNSEEN Notifications 
        booking.seen_by_guide = False
        booking.seen_by_traveler = True

        try:
            validate_minors_policy(experience, booking.adults, booking.children, booking.infants)
        except CoreValidationError as e:
            form.add_error(None, e.message)
            return render(request, "bookings/create.html", {"form": form, "experience": experience})

        booking.save()

        message = (
            f"¡Solicitud de reserva enviada!\n\n"
            f"Tu solicitud está pendiente de confirmación por el guía.\n\n"
            f"Experiencia: {booking.experience.title}\n"
            f"Fecha solicitada: {booking.date}\n\n"
            f"Grupo:\n"
            f"- Adultos: {booking.adults}\n"
            f"- Niños: {booking.children}\n"
            f"- Bebés: {booking.infants}\n\n"
            f"Desplazamiento: {booking.get_transport_mode_display()}\n"
            f"{'Punto de encuentro: ' + booking.pickup_notes + chr(10) if booking.pickup_notes else ''}"
            f"\nTotal estimado: {booking.total_price}€\n\n"
            f"Cuando el guía responda, te avisaremos.\n"
        )

        send_booking_status_email(
            to_email=booking.traveler.email,
            subject="Solicitud de reserva enviada - LanzaXperience",
            message=message,
        )

        messages.success(request, "Reserva enviada al guía.")
        return redirect("bookings:traveler_list")

    return render(request, "bookings/create.html", {"form": form, "experience": experience})


@login_required
def traveler_bookings(request):
    bookings = (
        Booking.objects.filter(traveler=request.user)
        .select_related("experience", "experience__guide")
    )
    return render(request, "bookings/traveler_list.html", {
        "bookings": bookings,
        "today": timezone.localdate(),
    })


@guide_required
def guide_bookings(request):
    bookings = (
        Booking.objects.filter(experience__guide=request.user)
        .select_related("experience", "traveler")
    )

    language_labels = dict(Language.objects.values_list("id", "name"))

    return render(request, "bookings/guide_list.html", {
        "bookings": bookings,
        "language_labels": language_labels,
    })

@login_required
def booking_detail(request, pk):
    booking = get_object_or_404(
        Booking.objects.select_related("experience", "experience__guide", "traveler"),
        pk=pk,
    )

    # Permissions
    if request.user == booking.traveler:
        if not booking.seen_by_traveler:
            booking.seen_by_traveler = True
            booking.save(update_fields=["seen_by_traveler"])

    elif request.user.is_guide() and booking.experience.guide == request.user:
        if not booking.seen_by_guide:
            booking.seen_by_guide = True
            booking.save(update_fields=["seen_by_guide"])

    else:
        messages.error(request, "No tienes permiso para ver esta reserva.")
        return redirect("pages:dashboard")

    # -------------------------
    # Flags UX for BTNS
    # -------------------------
    is_closed = booking.status in [Booking.Status.REJECTED, Booking.Status.CANCELED]
    has_started = booking_has_started(booking)

    is_pending_review = booking.status in [
        Booking.Status.CHANGE_REQUESTED,
        Booking.Status.CANCEL_REQUESTED,
    ]

    # ONLY ALLOW ACTIONS:
        # - not closed
        # - not started/passed
        # - not pending
    can_request_change = (not is_closed) and (not has_started) and (not is_pending_review)
    can_request_cancel = (not is_closed) and (not has_started) and (not is_pending_review)

    language_labels = dict(Language.objects.values_list("id", "name"))

    # Show free cxl ONLY if allowed
    show_free_cancel = can_request_cancel and can_cancel_free(booking)

    return render(request, "bookings/detail.html", {
        "booking": booking,
        "can_request_change": can_request_change,
        "can_request_cancel": can_request_cancel,
        "show_free_cancel": show_free_cancel,
        "has_started": has_started,  
        "language_labels": language_labels,
    })


@guide_required
def accept_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, experience__guide=request.user)
    if booking.status not in [Booking.Status.PENDING, Booking.Status.ACCEPTED]:
        messages.warning(request, "Esta reserva no se puede gestionar desde aquí.")
        return redirect("bookings:detail", pk=booking.pk)
    
    if request.method == "GET" and not booking.seen_by_guide:
        booking.seen_by_guide = True
        booking.save(update_fields=["seen_by_guide"])

    if request.method == "POST":
        form = BookingDecisionForm(request.POST, instance=booking)
        form.require_pickup_time = True
        if form.is_valid():
            booking = form.save(commit=False)

            try:
                validate_minors_policy(booking.experience, booking.adults, booking.children, booking.infants)
            except CoreValidationError as e:
                messages.error(request, e.message)
                return redirect("bookings:detail", pk=booking.pk)

            people = booking.people
            ok, msg = is_date_available(
                booking.experience,
                booking.date,
                people,
                exclude_booking_id=booking.id,
            )

            if not ok:
                messages.error(request, msg or "Ya no hay disponibilidad para esa fecha.")
                return redirect("bookings:detail", pk=booking.pk)

            booking.status = Booking.Status.ACCEPTED
            booking.seen_by_traveler = False
            booking.seen_by_guide = True
            if booking.responded_at is None:
                booking.responded_at = timezone.now()

            booking.save()

            try:
                booking.invoice
            except Invoice.DoesNotExist:
                create_invoice_from_booking(booking)

            send_booking_status_email(
                to_email=booking.traveler.email,
                subject="Reserva aceptada - LanzaXperience",
                message=(
                    f"¡Tu reserva ha sido CONFIRMADA!\n\n"
                    f"Experiencia: {booking.experience.title}\n"
                    f"Fecha: {booking.date}\n\n"
                    f"Grupo:\n"
                    f"- Adultos: {booking.adults}\n"
                    f"- Niños: {booking.children}\n"
                    f"- Bebés: {booking.infants}\n\n"
                    f"Transporte: {booking.get_transport_mode_display()}\n"
                    f"Punto de encuentro: {booking.pickup_notes or 'Por concretar con el guía'}\n\n"
                    f"Total: {booking.total_price}€\n\n"
                    f"Mensaje del guía:\n{booking.guide_response or '-'}\n"
                ),
            )

            messages.success(request, "Reserva aceptada.")
            return redirect("bookings:guide_list")
    else:
        form = BookingDecisionForm(instance=booking)

    return render(request, "bookings/decision.html", {"booking": booking, "form": form, "action": "accept"})


@guide_required
def reject_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, experience__guide=request.user)
    if booking.status != Booking.Status.PENDING:
        messages.warning(request, "Esta reserva ya fue gestionada y no se puede rechazar.")
        return redirect("bookings:detail", pk=booking.pk)
    
    if request.method == "GET" and not booking.seen_by_guide:
        booking.seen_by_guide = True
        booking.save(update_fields=["seen_by_guide"])


    if request.method == "POST":
        form = BookingDecisionForm(request.POST, instance=booking)
        form.require_guide_response = True
        if form.is_valid():
            booking = form.save(commit=False)
            booking.status = Booking.Status.REJECTED
            booking.seen_by_traveler = False
            booking.seen_by_guide = True
            if booking.responded_at is None:
                booking.responded_at = timezone.now()

            booking.save()

            send_booking_status_email(
                to_email=booking.traveler.email,
                subject="Reserva rechazada - LanzaXperience",
                message=(
                    f"Tu solicitud de reserva ha sido RECHAZADA.\n\n"
                    f"Experiencia: {booking.experience.title}\n"
                    f"Fecha solicitada: {booking.date}\n\n"
                    f"Grupo:\n"
                    f"- Adultos: {booking.adults}\n"
                    f"- Niños: {booking.children}\n"
                    f"- Bebés: {booking.infants}\n\n"
                    f"Transporte: {booking.get_transport_mode_display()}\n"
                    f"Punto de encuentro: {booking.pickup_notes or 'No especificado'}\n\n"
                    f"Precio por adulto: {booking.unit_price}€\n"
                    f"Total estimado: {booking.total_price}€\n\n"
                    f"Mensaje del guía:\n{booking.guide_response or '-'}\n"
                ),
            )

            messages.success(request, "Reserva rechazada.")
            return redirect("bookings:guide_list")
    else:
        form = BookingDecisionForm(instance=booking)

    return render(request, "bookings/decision.html", {
        "booking": booking,
        "form": form,
        "action": "reject",
    })


@login_required
def request_booking_change(request, pk):
    booking = get_object_or_404(Booking, pk=pk, traveler=request.user)
    
    # No changes allowed if started/done
    if booking_has_started(booking):
        messages.error(request, "Esta experiencia ya ha comenzado o ya pasó. No se puede solicitar un cambio.")
        return redirect("bookings:detail", pk=booking.pk)

    # No changes allowed if cxl/rejected
    if booking.status in [Booking.Status.REJECTED, Booking.Status.CANCELED]:
        messages.error(request, "No puedes modificar una reserva rechazada o cancelada.")
        return redirect("bookings:detail", pk=booking.pk)

    # Avoid new request if pending to review.
    if booking.status in [Booking.Status.CHANGE_REQUESTED, Booking.Status.CANCEL_REQUESTED]:
        messages.warning(request, "Ya tienes una solicitud pendiente. Espera a que el guía la gestione.")
        return redirect("bookings:detail", pk=booking.pk)

    form = BookingChangeRequestForm(request.POST or None, booking=booking, instance=booking)

    if request.method == "POST" and form.is_valid():
        booking.extras = booking.extras or {}
        booking.extras["pre_change_status"] = booking.status
        booking.extras.pop("change_blocked_reason", None)

        clean = form.cleaned_data.copy()

        # Calculate values
        proposed_adults = clean.get("adults")
        if proposed_adults is None:
            proposed_adults = booking.adults

        proposed_children = clean.get("children")
        if proposed_children is None:
            proposed_children = booking.children

        proposed_infants = clean.get("infants")
        if proposed_infants is None:
            proposed_infants = booking.infants

        # VALIDATION
        try:
            validate_minors_policy(booking.experience, proposed_adults, proposed_children, proposed_infants)
        except CoreValidationError as e:
            form.add_error(None, e.message)
            return render(request, "bookings/request_change.html", {"booking": booking, "form": form})

        if clean.get("date"):
            clean["date"] = clean["date"].isoformat()

        # LANG Label
        pl = clean.get("preferred_language")
        if pl:
            if isinstance(pl, Language):
                clean["preferred_language"] = pl.pk
                clean["preferred_language_label"] = pl.name
            else:
                lang = Language.objects.filter(pk=pl).only("id", "name").first()
                clean["preferred_language"] = int(pl)
                clean["preferred_language_label"] = lang.name if lang else str(pl)

        booking.extras["change_request"] = clean
        booking.status = Booking.Status.CHANGE_REQUESTED
        booking.seen_by_guide = False
        booking.seen_by_traveler = True

        booking.save(update_fields=["extras", "status", "seen_by_guide", "seen_by_traveler", "updated_at"])
        messages.success(request, "Solicitud de cambio enviada al guía.")
        return redirect("bookings:traveler_list")

    return render(request, "bookings/request_change.html", {"booking": booking, "form": form})


@guide_required
def decide_change_request(request, pk, decision):
    booking = get_object_or_404(Booking, pk=pk, experience__guide=request.user)

    if booking.status != Booking.Status.CHANGE_REQUESTED:
        messages.warning(request, "No hay solicitud de cambio pendiente.")
        return redirect("bookings:detail", pk=booking.pk)

    change = (booking.extras or {}).get("change_request")
    if not change:
        messages.error(request, "Solicitud de cambio inválida.")
        return redirect("bookings:detail", pk=booking.pk)

    booking.extras = booking.extras or {}
    prev_status = booking.extras.get("pre_change_status") or Booking.Status.PENDING

    # -------------------------
    # REJECT - manually
    # -------------------------
    if decision == "reject":
        booking.extras.pop("change_request", None)
        booking.extras.pop("pre_change_status", None)

        booking.extras["last_update"] = {
            "type": "change",
            "decision": "rejected",
            "reason": "guide",
            "at": timezone.now().isoformat(),
        }

        # IF CHANGE: reject - ALLOW free cxl
        booking.extras["free_cancel_override"] = {
            "reason": "change_rejected",
            "set_at": timezone.now().isoformat(),
        }

        booking.status = prev_status
        booking.responded_at = timezone.now()
        booking.seen_by_traveler = False
        booking.seen_by_guide = True
        booking.save()

        cancel_url = request.build_absolute_uri(
            reverse("bookings:request_cancel", kwargs={"pk": booking.pk})
        )
        detail_url = request.build_absolute_uri(
            reverse("bookings:detail", kwargs={"pk": booking.pk})
        )

        send_booking_status_email(
            to_email=booking.traveler.email,
            subject="Cambio de fecha rechazado - LanzaXperience",
            message=(
                f"El guía ha rechazado tu solicitud de cambio.\n\n"
                f"Experiencia: {booking.experience.title}\n"
                f"Fecha actual: {booking.date}\n\n"
                f"Puedes elegir:\n"
                f"1) Mantener la fecha original (no tienes que hacer nada).\n"
                f"2) Cancelar sin penalización (aunque falten menos de 48h).\n\n"
                f"👉 Cancelar gratis: {cancel_url}\n"
                f"👉 Ver reserva: {detail_url}\n\n"
                f"Si necesitas ayuda, contacta con soporte."
            ),
        )

        messages.success(request, "Cambio rechazado.")
        return redirect("bookings:guide_list")

    # -------------------------
    # ACCEPT
    # -------------------------

    # Apply changes to memory
    if change.get("date"):
        booking.date = date.fromisoformat(change["date"])
        booking.pickup_time = None
        booking.meeting_point = ""

    booking.adults = change.get("adults", booking.adults)
    booking.children = change.get("children", booking.children)
    booking.infants = change.get("infants", booking.infants)

    # VALIDATE POLOCY
    try:
        validate_minors_policy(booking.experience, booking.adults, booking.children, booking.infants)
    except CoreValidationError as e:

        booking.extras.pop("change_request", None)
        booking.extras.pop("pre_change_status", None)

        # Register update - traveler/UI
        booking.extras["last_update"] = {
            "type": "change",
            "decision": "rejected",
            "reason": "policy",
            "message": e.message,
            "at": timezone.now().isoformat(),
        }

        booking.extras["free_cancel_override"] = {
            "reason": "change_rejected",
            "set_at": timezone.now().isoformat(),
        }

        # Maintain old state
        booking.status = prev_status
        booking.responded_at = timezone.now()
        booking.seen_by_guide = True
        booking.seen_by_traveler = False

        booking.save(update_fields=[
            "extras", "status", "responded_at",
            "seen_by_guide", "seen_by_traveler", "updated_at"
        ])

        messages.error(request, e.message)
        return redirect("bookings:guide_list")

    # IF pass - apply
    booking.pickup_notes = change.get("pickup_notes", booking.pickup_notes)
    pl_id = change.get("preferred_language")
    if pl_id:
        booking.preferred_language_id = pl_id   # type: ignore[attr-defined]

    booking.notes = change.get("notes", booking.notes)

    # Recalculate uodated info
    unit_price = Decimal(str(booking.experience.price or "0"))
    booking.unit_price = unit_price
    children_unit = unit_price * Decimal("0.5")
    booking.total_price = (unit_price * Decimal(booking.adults or 0)) + (children_unit * Decimal(booking.children or 0))

    # Vlidate availability
    ok, msg = is_date_available(
        booking.experience,
        booking.date,
        booking.people,
        exclude_booking_id=booking.pk,
    )
    if not ok:
        messages.error(request, msg or "Ya no hay disponibilidad para esa fecha.")
        return redirect("bookings:detail", pk=booking.pk)

    # CLEAN application
    booking.extras.pop("change_request", None)
    booking.extras.pop("pre_change_status", None)
    booking.extras.pop("free_cancel_override", None) 

    booking.extras["last_update"] = {
        "type": "change",
        "decision": "accepted",
        "at": timezone.now().isoformat(),
    }

    booking.status = prev_status
    booking.responded_at = timezone.now()
    booking.seen_by_traveler = False
    booking.seen_by_guide = True
    booking.save()

    messages.success(request, "Cambio aceptado. Confirma la hora y el punto de encuentro.")
    return redirect("bookings:accept", pk=booking.pk)


@guide_required
def decide_cancel_request(request, pk, decision):
    booking = get_object_or_404(Booking, pk=pk, experience__guide=request.user)

    # Pending application MUST exist
    if booking.status != Booking.Status.CANCEL_REQUESTED:
        messages.warning(request, "No hay solicitud de cancelación pendiente.")
        return redirect("bookings:detail", pk=booking.pk)

    # Guard: for free cxl
    if can_cancel_free(booking) and decision == "reject":
        messages.warning(
            request,
            "Esta cancelación es gratuita según la política y no puede ser rechazada."
        )
        return redirect("bookings:detail", pk=booking.pk)

    booking.extras = booking.extras or {}

    # IMG of old state
    pre_status = booking.extras.get("pre_cancel_status") or Booking.Status.ACCEPTED

    if decision == "reject":
        # Clean request
        booking.extras.pop("cancel_request", None)

        # Previous state
        booking.status = pre_status
        booking.responded_at = timezone.now()
        booking.seen_by_traveler = False
        booking.seen_by_guide = True

        booking.extras["last_update"] = {
            "type": "cancel",
            "decision": "rejected",
            "at": timezone.now().isoformat(),
        }

        booking.save(update_fields=[
            "extras", "status", "responded_at",
            "seen_by_traveler", "seen_by_guide", "updated_at"
        ])

        rectificate_booking_invoice_if_needed(
            booking,
            reason="Cancelación rechazada por el guía",
        )

        send_booking_status_email(
            to_email=booking.traveler.email,
            subject="Solicitud de cancelación rechazada - LanzaXperience",
            message=(
                f"El guía ha rechazado tu solicitud de cancelación.\n\n"
                f"Experiencia: {booking.experience.title}\n"
                f"Fecha: {booking.date}\n\n"
                f"Si necesitas ayuda, contacta con soporte."
            ),
        )

        messages.success(request, "Cancelación rechazada.")
        return redirect("bookings:guide_list")

    # --- ACCEPT Cxl ---
    booking.extras.pop("cancel_request", None)
    booking.extras.pop("pre_cancel_status", None)

    booking.status = Booking.Status.CANCELED
    booking.responded_at = timezone.now()
    booking.seen_by_traveler = False
    booking.seen_by_guide = True

    booking.extras["last_update"] = {
        "type": "cancel",
        "decision": "accepted",
        "at": timezone.now().isoformat(),
    }

    booking.save(update_fields=[
        "extras", "status", "responded_at",
        "seen_by_traveler", "seen_by_guide", "updated_at"
    ])

    send_booking_status_email(
        to_email=booking.traveler.email,
        subject="Solicitud de cancelación aceptada - LanzaXperience",
        message=(
            f"Tu solicitud de cancelación para {booking.experience.title} el {booking.date} "
            f"ha sido aceptada.\n\n"
            f"Si corresponde algún reembolso, se procesará según la política aplicable."
        ),
    )

    messages.success(request, "Reserva cancelada correctamente.")
    return redirect("bookings:guide_list")


@login_required
def request_booking_cancel(request, pk):
    booking = get_object_or_404(Booking, pk=pk, traveler=request.user)

    # If STARTED/DONE - cxl not allowed
    if booking_has_started(booking):
        messages.error(request, "Esta experiencia ya ha comenzado o ya pasó. No se puede cancelar.")
        return redirect("bookings:detail", pk=booking.pk)

    # If CLOSED - Cxl not allowed
    if booking.status in [Booking.Status.REJECTED, Booking.Status.CANCELED]:
        messages.error(request, "Esta reserva no se puede cancelar.")
        return redirect("bookings:detail", pk=booking.pk)

    # AVOID duplicate flow 
    if booking.status == Booking.Status.CANCEL_REQUESTED:
        messages.info(request, "Ya tienes una solicitud de cancelación pendiente.")
        return redirect("bookings:detail", pk=booking.pk)

    if booking.status == Booking.Status.CHANGE_REQUESTED:
        messages.warning(
            request,
            "Tienes una solicitud de cambio pendiente. Espera a que el guía responda antes de cancelar."
        )
        return redirect("bookings:detail", pk=booking.pk)

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()

        # --- DIRECT Cxl - Policy ---
        if can_cancel_free(booking):
            booking.status = Booking.Status.CANCELED
            booking.responded_at = timezone.now()
            booking.seen_by_guide = False
            booking.seen_by_traveler = True
            booking.extras = booking.extras or {}

            booking.extras.pop("free_cancel_override", None)
            booking.extras.pop("cancel_request", None)
            booking.extras.pop("pre_cancel_status", None)

            booking.extras["last_update"] = {
                "type": "cancel",
                "decision": "traveler_canceled_free",
                "at": timezone.now().isoformat(),
            }
            if reason:
                booking.extras["last_update"]["reason"] = reason

            booking.save(update_fields=[
                "status", "responded_at",
                "seen_by_guide", "seen_by_traveler",
                "extras", "updated_at"
            ])

            rectificate_booking_invoice_if_needed(
                booking,
                reason="Cancelación gratis (48h) por el viajero",
            )

            # EMAIL notification - Cxl
            send_booking_status_email(
                to_email=booking.traveler.email,
                subject="Reserva cancelada - LanzaXperience",
                message=(
                    f"Tu reserva para {booking.experience.title} el {booking.date} "
                    f"ha sido cancelada correctamente.\n\n"
                    f"{'Motivo: ' + reason if reason else ''}"
                ),
            )

            # GUIDE - email notification Cxl
            send_booking_status_email(
                to_email=booking.experience.guide.email,
                subject="Reserva cancelada por el viajero - LanzaXperience",
                message=(
                    f"El viajero ha cancelado una reserva.\n\n"
                    f"Experiencia: {booking.experience.title}\n"
                    f"Fecha: {booking.date}\n"
                    f"Viajero: {booking.traveler.username}\n\n"
                    f"{'Motivo: ' + reason if reason else ''}"
                ),
            )

            messages.success(request, "Reserva cancelada correctamente.")
            return redirect("bookings:traveler_list")

        # --- OUTSIDE - POLICY RULE ---
        booking.extras = booking.extras or {}
        booking.extras["pre_cancel_status"] = booking.status
        booking.extras["cancel_request"] = {"reason": reason}

        booking.status = Booking.Status.CANCEL_REQUESTED
        booking.seen_by_guide = False
        booking.seen_by_traveler = True

        booking.extras["last_update"] = {
            "type": "cancel",
            "decision": "requested",
            "at": timezone.now().isoformat(),
        }

        booking.save(update_fields=[
            "extras", "status",
            "seen_by_guide", "seen_by_traveler",
            "updated_at"
        ])

        messages.success(request, "Solicitud de cancelación enviada al guía.")
        return redirect("bookings:traveler_list")

    override_free = (
        (booking.extras or {}).get("free_cancel_override", {}).get("reason") == "change_rejected"
    )

    return render(request, "bookings/request_cancel.html", {
        "booking": booking,
        "show_free_cancel": can_cancel_free(booking),
        "override_free": override_free,
    })
