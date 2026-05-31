"""Generate a tailored Kaleya master_prompt for a tenant from their website.

Usage:
  python manage.py generate_master_prompt --client-id 1 --website-url https://mikesbarber.com
  python manage.py generate_master_prompt --client-id 1 --website-url https://... --print-only

The brief is written to ClientApiSettings.master_prompt and automatically
picked up by build_voice_prompt() on the next voice/SMS/WhatsApp turn.
"""

from django.core.management.base import BaseCommand, CommandError

from ai_agent.auto_master_prompt import (
    fetch_website_snapshot,
    generate_master_prompt_from_website,
)
from clients.models import BusinessClient


class Command(BaseCommand):
    help = "Generate a per-tenant master_prompt from a website URL."

    def add_arguments(self, parser):
        parser.add_argument("--client-id", type=int, required=True, help="BusinessClient ID")
        parser.add_argument(
            "--website-url", type=str, required=True,
            help="Public website URL for the salon (https://...)",
        )
        parser.add_argument(
            "--print-only", action="store_true",
            help="Generate and print but do NOT save to ClientApiSettings.",
        )
        parser.add_argument(
            "--show-snapshot", action="store_true",
            help="Also print the scraped page snapshot Claude was given.",
        )

    def handle(self, *args, **opts):
        client = BusinessClient.objects.filter(id=opts["client_id"]).first()
        if not client:
            raise CommandError(f"BusinessClient with id={opts['client_id']} not found.")

        self.stdout.write(f"Client: {client} (id={client.id})")
        self.stdout.write(f"Website: {opts['website_url']}")

        if opts["show_snapshot"]:
            snapshot = fetch_website_snapshot(opts["website_url"])
            self.stdout.write("\n--- WEBSITE SNAPSHOT ---")
            self.stdout.write(f"title: {snapshot.get('title','')}")
            self.stdout.write(f"desc:  {snapshot.get('description','')}")
            body = snapshot.get("body", "")
            self.stdout.write(f"body:  {body[:500]}{'...' if len(body) > 500 else ''}")
            self.stdout.write("------------------------\n")

        try:
            brief = generate_master_prompt_from_website(
                client, opts["website_url"], save=not opts["print_only"],
            )
        except Exception as exc:
            raise CommandError(f"Generation failed: {exc}") from exc

        if not brief:
            self.stdout.write(self.style.WARNING(
                "No persona generated (insufficient website signal or Claude opted to skip)."
            ))
            return

        self.stdout.write("\n--- GENERATED MASTER PROMPT ---")
        self.stdout.write(brief)
        self.stdout.write("-------------------------------\n")

        if opts["print_only"]:
            self.stdout.write(self.style.NOTICE(
                "--print-only set: NOT saved to ClientApiSettings.master_prompt."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Saved to ClientApiSettings.master_prompt for client {client.id}."
            ))
