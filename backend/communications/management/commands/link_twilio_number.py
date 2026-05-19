"""Link a Twilio phone number to a Kaleya BusinessClient.

Usage:
    python manage.py link_twilio_number --client 1 --number +15551234567

This creates/updates an IntegrationConnection(provider="phone") whose
`public_number` matches the dialed number, so voice_incoming() can find
the tenant when Twilio posts the webhook.
"""

from django.core.management.base import BaseCommand, CommandError

from clients.models import BusinessClient
from integrations.models import IntegrationConnection


class Command(BaseCommand):
    help = "Link a Twilio phone number to a BusinessClient (so calls route to it)."

    def add_arguments(self, parser):
        parser.add_argument("--client", required=True, help="BusinessClient ID")
        parser.add_argument("--number", required=True, help="Twilio number in E.164 (e.g. +15551234567)")
        parser.add_argument("--disconnect", action="store_true", help="Remove the link instead of creating it")

    def handle(self, *args, **opts):
        client_id = opts["client"]
        number = opts["number"].strip()
        disconnect = opts["disconnect"]

        try:
            business = BusinessClient.objects.get(id=client_id)
        except BusinessClient.DoesNotExist:
            raise CommandError(f"BusinessClient {client_id} not found.")

        if disconnect:
            deleted, _ = IntegrationConnection.objects.filter(
                business_client=business, provider="phone", public_number=number
            ).delete()
            if deleted:
                self.stdout.write(self.style.SUCCESS(f"Unlinked {number} from {business}."))
            else:
                self.stdout.write(self.style.WARNING(f"No phone integration found for {number}."))
            return

        conn, created = IntegrationConnection.objects.update_or_create(
            business_client=business,
            provider="phone",
            defaults={
                "public_number": number,
                "enabled": True,
                "status": "connected",
                "config": {"twilio": True},
                "last_error": "",
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} phone integration for {business}: {number}"))
        self.stdout.write(
            f"\nIn Twilio Console set this number's Voice webhook to:\n"
            f"  https://www.aikaleya.com/api/communications/voice/incoming/  (POST)\n"
            f"And status callback to:\n"
            f"  https://www.aikaleya.com/api/communications/voice/status/0/  (POST)  ← session id is rewritten by Twilio automatically when status callback is per-call"
        )
