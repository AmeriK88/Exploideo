from django.utils import timezone

from apps.billing.models import Invoice
from apps.billing.services_rectification import create_rectificative_for_invoice

from django.core.exceptions import ValidationError


def rectificate_booking_invoice_if_needed(booking, reason: str) -> None:
    """
    Genera factura rectificativa si:
    - existe factura
    - está emitida
    - NO ha sido rectificada antes

    Es idempotente y deja rastro en booking.extras (auditoría).
    """
    try:
        inv = booking.invoice
    except Invoice.DoesNotExist:
        return

    if inv.status != Invoice.Status.ISSUED:
        return

    booking.extras = booking.extras or {}
    billing = booking.extras.get("billing") or {}

    if billing.get("rectified") is True:
        return

    rect = create_rectificative_for_invoice(inv, reason=reason)

    booking.extras["billing"] = {
        "rectified": True,
        "at": timezone.now().isoformat(),
        "invoice_number": inv.number,
        "rectificative_number": rect.number,
        "reason": reason,
    }

    booking.save(update_fields=["extras", "updated_at"])
    

def validate_minors_policy(experience, adults: int, children: int, infants: int):
    minors = (children or 0) + (infants or 0)

    # Difícil: NO menores
    if experience.difficulty == "hard" and minors > 0:
        raise ValidationError("Esta experiencia es DIFÍCIL y no permite menores.")

    # Moderada: menores OK, pero acompañados (mínimo 1 adulto)
    if experience.difficulty == "moderate" and minors > 0 and (adults or 0) <= 0:
        raise ValidationError("Los menores solo pueden asistir acompañados de al menos 1 adulto.")