from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from appointments.models import Appointment


class Command(BaseCommand):
    help = "Deletes test appointments (is_test=True) older than 60 minutes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=60,
            help="Delete test appointments older than this many minutes (default: 60).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        minutes = options["minutes"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(minutes=minutes)

        qs = Appointment.objects.filter(is_test=True, created_at__lt=cutoff)
        count = qs.count()

        if count == 0:
            self.stdout.write("No expired test appointments found.")
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] Would delete {count} test appointment(s) older than {minutes} minutes."
                )
            )
            return

        deleted, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {deleted} test appointment(s) older than {minutes} minutes."
            )
        )
