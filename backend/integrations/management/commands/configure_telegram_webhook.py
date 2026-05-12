from django.core.management.base import BaseCommand, CommandError

from integrations.models import IntegrationConnection
from integrations.services import configure_telegram_webhook


class Command(BaseCommand):
    help = "Configures Telegram setWebhook for one Kaleya Telegram integration."

    def add_arguments(self, parser):
        parser.add_argument("--connection-id", type=int, default=None, help="IntegrationConnection id.")
        parser.add_argument("--client-id", type=int, default=None, help="BusinessClient id for the Telegram integration.")
        parser.add_argument("--url", default="", help="Public Telegram webhook URL. If omitted, saved webhook_url is used.")
        parser.add_argument(
            "--drop-pending-updates",
            action="store_true",
            help="Tell Telegram to drop queued updates before enabling the webhook.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Validate and print what would be configured.")

    def handle(self, *args, **options):
        connection_id = options["connection_id"]
        client_id = options["client_id"]
        if not connection_id and not client_id:
            raise CommandError("Unesi --connection-id ili --client-id.")

        queryset = IntegrationConnection.objects.select_related("business_client").filter(provider="telegram")
        if connection_id:
            connection = queryset.filter(id=connection_id).first()
        else:
            connection = queryset.filter(business_client_id=client_id).first()

        if not connection:
            raise CommandError("Telegram integracija nije pronadjena.")

        config = connection.config or {}
        webhook_url = (options["url"] or connection.webhook_url or "").strip()
        if not config.get("bot_token"):
            raise CommandError("Telegram bot token nije upisan u admin panelu.")
        if not config.get("webhook_secret"):
            raise CommandError("Telegram webhook secret nije upisan u admin panelu.")
        if not webhook_url:
            raise CommandError("Webhook URL nije upisan. Prosledi --url ili ga sacuvaj u admin panelu.")

        self.stdout.write(f"Client: {connection.business_client_id} - {connection.business_client}")
        self.stdout.write(f"Connection: {connection.id}")
        self.stdout.write(f"Webhook URL: {webhook_url}")
        self.stdout.write(f"Secret configured: {'yes' if config.get('webhook_secret') else 'no'}")
        self.stdout.write(f"Bot token configured: {'yes' if config.get('bot_token') else 'no'}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Dry run: Telegram setWebhook nije pozvan."))
            return

        try:
            response = configure_telegram_webhook(
                connection,
                webhook_url=webhook_url,
                drop_pending_updates=options["drop_pending_updates"],
            )
        except Exception as exc:
            connection.status = "error"
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            raise CommandError(f"Telegram webhook nije konfigurisan: {exc}") from exc

        self.stdout.write(self.style.SUCCESS("Telegram webhook je konfigurisan."))
        description = response.get("description")
        if description:
            self.stdout.write(description)
