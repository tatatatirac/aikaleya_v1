import json
import secrets
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


DEFAULT_EVENTS = [
    "subscription_created",
    "subscription_updated",
    "subscription_resumed",
    "subscription_payment_success",
    "subscription_payment_failed",
    "subscription_cancelled",
    "subscription_expired",
    "subscription_paused",
]


class Command(BaseCommand):
    help = "Creates a Lemon Squeezy webhook for Kaleya billing activation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            required=True,
            help="Public webhook URL, for example https://aikaleya.com/api/billing/lemonsqueezy/webhook/",
        )
        parser.add_argument(
            "--secret",
            default="",
            help="Webhook signing secret. If omitted, the command uses .env or generates one.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print payload without creating the webhook.",
        )

    def handle(self, *args, **options):
        api_key = settings.KALEYA_LEMONSQUEEZY_API_KEY
        store_id = settings.KALEYA_LEMONSQUEEZY_STORE_ID
        if not api_key:
            raise CommandError("LEMONSQUEEZY_API_KEY nije podesen u .env fajlu.")
        if not store_id:
            raise CommandError("LEMONSQUEEZY_STORE_ID nije podesen u .env fajlu.")

        secret = options["secret"] or settings.KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET
        generated_secret = False
        if not secret:
            secret = secrets.token_urlsafe(32)
            generated_secret = True

        payload = {
            "data": {
                "type": "webhooks",
                "attributes": {
                    "url": options["url"],
                    "events": DEFAULT_EVENTS,
                    "secret": secret,
                    "test_mode": settings.KALEYA_LEMONSQUEEZY_TEST_MODE,
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": str(store_id),
                        }
                    }
                },
            }
        }

        if options["dry_run"]:
            safe_payload = json.loads(json.dumps(payload))
            safe_payload["data"]["attributes"]["secret"] = "***"
            self.stdout.write(json.dumps(safe_payload, indent=2))
            if generated_secret:
                self.stdout.write(self.style.WARNING(f"Generated secret for .env: {secret}"))
            return

        request = urllib.request.Request(
            f"{settings.KALEYA_LEMONSQUEEZY_API_BASE}/v1/webhooks",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise CommandError(f"Lemon Squeezy webhook greska {exc.code}: {body}") from exc
        except Exception as exc:
            raise CommandError(f"Lemon Squeezy webhook nije kreiran: {exc}") from exc

        webhook = data.get("data") or {}
        attrs = webhook.get("attributes") or {}
        self.stdout.write(self.style.SUCCESS(f"Webhook created: id={webhook.get('id')} url={attrs.get('url')}"))
        if generated_secret:
            self.stdout.write(self.style.WARNING("Upisi ovaj secret u .env kao LEMONSQUEEZY_WEBHOOK_SECRET:"))
            self.stdout.write(secret)
