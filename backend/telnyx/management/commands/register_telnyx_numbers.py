"""
Management command to register Telnyx test numbers to a business client.

Usage:
    python manage.py register_telnyx_numbers --client-id 1
    python manage.py register_telnyx_numbers --client-email owner@salon.com
    python manage.py register_telnyx_numbers  # uses first active client
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from clients.models import BusinessClient
from telnyx.models import TelnyxPhoneNumber


class Command(BaseCommand):
    help = "Register Telnyx test phone numbers to a business client"

    def add_arguments(self, parser):
        parser.add_argument("--client-id", type=int, help="BusinessClient ID")
        parser.add_argument("--client-email", type=str, help="BusinessClient owner email")
        parser.add_argument("--dry-run", action="store_true", help="Show what would be done without saving")

    def handle(self, *args, **options):
        # Find business client
        client = None
        if options["client_id"]:
            client = BusinessClient.objects.filter(id=options["client_id"]).first()
        elif options["client_email"]:
            client = BusinessClient.objects.filter(
                profile__user__email=options["client_email"]
            ).first()

        if not client:
            client = BusinessClient.objects.filter(is_active=True).first()

        if not client:
            self.stderr.write(self.style.ERROR("No active business client found."))
            return

        self.stdout.write(f"Using client: {client} (ID: {client.id})")

        numbers_to_register = []

        usa_number = settings.KALEYA_TELNYX_TEST_NUMBER_USA
        if usa_number:
            numbers_to_register.append((usa_number, "US", True, True))

        ca_number = settings.KALEYA_TELNYX_TEST_NUMBER_CA
        if ca_number:
            numbers_to_register.append((ca_number, "CA", True, True))

        if not numbers_to_register:
            self.stderr.write(self.style.WARNING(
                "No test numbers found in .env. "
                "Set TELNYX_TEST_NUMBER_USA and/or TELNYX_TEST_NUMBER_CA."
            ))
            return

        for phone, country, voice, sms in numbers_to_register:
            if options["dry_run"]:
                self.stdout.write(f"  [DRY RUN] Would register: {phone} ({country}) → {client}")
                continue

            obj, created = TelnyxPhoneNumber.objects.update_or_create(
                phone_number=phone,
                defaults={
                    "business_client": client,
                    "country_code": country,
                    "voice_enabled": voice,
                    "sms_enabled": sms,
                    "is_active": True,
                },
            )
            status = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  {status}: {phone} ({country}) → {client}"))

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("\nDone! Numbers registered."))
            self.stdout.write("Now run migrations if you haven't:")
            self.stdout.write("  python manage.py makemigrations telnyx")
            self.stdout.write("  python manage.py migrate")
