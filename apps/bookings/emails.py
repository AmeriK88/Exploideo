from django.conf import settings
from django.core.mail import send_mail


def send_booking_status_email(*, to_email: str, subject: str, message: str) -> None:
    if not to_email:
        return

    fail_silently = not getattr(settings, "DEBUG", False)

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None) or "no-reply@exploideo.com",
        recipient_list=[to_email],
        fail_silently=fail_silently,
    )
