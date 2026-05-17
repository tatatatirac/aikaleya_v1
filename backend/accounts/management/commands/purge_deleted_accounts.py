from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Hard-delete user accounts that have passed their 30-day deletion grace period."

    def handle(self, *args, **options):
        to_delete = User.objects.filter(
            is_active=False,
            profile__deletion_scheduled_at__lte=timezone.now(),
        )
        count = to_delete.count()
        to_delete.delete()
        self.stdout.write(f"Purged {count} account(s).")
