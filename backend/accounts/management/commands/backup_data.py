from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates a JSON backup of Kaleya business data."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="", help="Optional exact output path for the backup JSON file.")

    def handle(self, *args, **options):
        backup_dir = Path(getattr(settings, "DATA_BACKUP_DIR", settings.BASE_DIR.parent / "backups"))
        backup_dir.mkdir(parents=True, exist_ok=True)

        output = Path(options["output"]) if options["output"] else backup_dir / f"kaleya-backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        output.parent.mkdir(parents=True, exist_ok=True)

        with output.open("w", encoding="utf-8") as file_obj:
            call_command(
                "dumpdata",
                natural_foreign=True,
                natural_primary=True,
                indent=2,
                exclude=[
                    "admin.logentry",
                    "contenttypes",
                    "sessions.session",
                    "authtoken.token",
                ],
                stdout=file_obj,
            )

        self.stdout.write(self.style.SUCCESS(f"Kaleya backup je sacuvan: {output}"))
