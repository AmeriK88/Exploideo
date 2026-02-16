from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import Q

from apps.bookings.models import Booking
from .models import Invoice

@login_required
def invoice_detail_by_booking(request, booking_pk):
    booking = get_object_or_404(
        Booking.objects.select_related("experience", "experience__guide", "traveler"),
        pk=booking_pk,
    )

    if not (
        request.user == booking.traveler
        or (request.user.is_guide() and booking.experience.guide == request.user)
    ):
        messages.error(request, "No tienes permiso para ver esta factura.")
        return redirect("pages:dashboard")

    try:
        invoice = booking.invoice
    except Invoice.DoesNotExist:
        messages.warning(request, "Esta reserva aún no tiene factura.")
        return redirect("bookings:detail", pk=booking.pk)

    return render(request, "billing/invoice_detail.html", {"invoice": invoice, "booking": booking})

@login_required
def my_invoices(request):
    """
    Traveler: ve sus facturas (incluye rectificativas porque comparten customer).
    Guide: ve facturas de reservas de sus experiencias + rectificativas de esas facturas.
    """
    qs = Invoice.objects.select_related(
        "booking", "booking__experience", "booking__experience__guide",
        "rectifies", "rectifies__booking", "rectifies__booking__experience", "rectifies__booking__experience__guide",
        "customer",
    )

    if request.user.is_guide():
        qs = qs.filter(
            Q(booking__experience__guide=request.user) |
            Q(rectifies__booking__experience__guide=request.user)
        )
    else:
        qs = qs.filter(customer=request.user)

    qs = qs.order_by("-created_at")

    return render(request, "billing/invoice_list.html", {"invoices": qs})

@login_required
def invoice_detail(request, pk: int):
    """
    Detalle de una factura por ID.
    Soporta STANDARD y RECTIFICATIVE.
    Permisos:
        - Traveler: si es el customer de esa factura
        - Guide: si la factura está asociada a una booking de sus experiencias
                o si es rectificativa y la booking está en la factura original.
    """
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "booking",
            "booking__experience",
            "booking__experience__guide",
            "customer",
            "rectifies",
            "rectifies__booking",
            "rectifies__booking__experience",
            "rectifies__booking__experience__guide",
        ),
        pk=pk,
    )

    user = request.user

    allowed = Invoice.objects.filter(
        Q(pk=invoice.pk) &
        (
            Q(customer=user) |
            Q(booking__experience__guide=user) |
            Q(rectifies__booking__experience__guide=user)
        )
    ).exists()

    if not allowed:
        messages.error(request, "No tienes permiso para ver esta factura.")
        return redirect("pages:dashboard")

    # Acceso seguro a la booking: Pylance no infiere que rectifies_id implique rectifies != None,
    # así que comprobamos explícitamente para evitar advertencias sobre atributos de None.
    if invoice.booking is not None:
        booking = invoice.booking
    elif invoice.rectifies is not None:
        booking = invoice.rectifies.booking
    else:
        booking = None

    return render(request, "billing/invoice_detail.html", {"invoice": invoice, "booking": booking})


