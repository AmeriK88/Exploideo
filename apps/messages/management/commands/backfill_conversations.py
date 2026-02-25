from django.core.management.base import BaseCommand

from apps.bookings.models import Booking
from apps.messages.models import Conversation
from apps.messages.services import ensure_conversation_for_accepted_booking, MessagingDomainError


class Command(BaseCommand):
    help = "Create missing conversations for already accepted bookings."

    def handle(self, *args, **options):
        qs = Booking.objects.filter(status=Booking.Status.ACCEPTED)
        total = qs.count()
        created = 0
        skipped = 0
        failed = 0

        for booking in qs.iterator():
            if Conversation.objects.filter(booking=booking).exists():
                skipped += 1
                continue
            try:
                ensure_conversation_for_accepted_booking(booking)
                created += 1
            except MessagingDomainError:
                failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. accepted={total} created={created} skipped={skipped} failed={failed}"
        ))