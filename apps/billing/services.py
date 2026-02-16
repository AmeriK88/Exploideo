from decimal import Decimal
from django.db import transaction

from apps.billing.models import Invoice, InvoiceItem
from apps.bookings.models import Booking


def create_invoice_from_booking(booking: Booking) -> Invoice:
    # 1) Si ya existe factura, devolverla
    try:
        return booking.invoice
    except Invoice.DoesNotExist:
        pass

    # 2) Crear de forma segura 
    with transaction.atomic():
        # Lock sobre la booking para evitar carreras
        booking = (
            Booking.objects.select_for_update()
            .select_related("traveler", "experience")
            .get(pk=booking.pk)
        )

        try:
            return booking.invoice
        except Invoice.DoesNotExist:
            pass

        invoice = Invoice.objects.create(
            booking=booking, 
            customer=booking.traveler,
            customer_name=(booking.traveler.get_full_name() or booking.traveler.username),
            customer_email=booking.traveler.email,
            currency="EUR",
        )

        InvoiceItem.objects.create(
            invoice=invoice,
            description=booking.experience.title,
            quantity=1,
            unit_price=booking.total_price,
            tax_rate=Decimal("7.00"),
        )

        invoice.issue()
        return invoice
