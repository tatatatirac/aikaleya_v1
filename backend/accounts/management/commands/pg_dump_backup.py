import os
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates a PostgreSQL binary dump of the Kaleya database using pg_dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Optional exact output path for the .dump file.",
        )

    def handle(self, *args, **options):
        db_url = os.getenv("DATABASE_URL", "")
        if not db_url:
            self.stderr.write(self.style.ERROR("DATABASE_URL is not set in environment."))
            return

        try:
            parsed = urllib.parse.urlparse(db_url)
            db_name = parsed.path.lstrip("/")
            db_user = parsed.username or ""
            db_password = parsed.password or ""
            db_host = parsed.hostname or "localhost"
            db_port = str(parsed.port or 5432)
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Could not parse DATABASE_URL: {exc}"))
            return

        if not db_name:
            self.stderr.write(self.style.ERROR("DATABASE_URL does not contain a database name."))
            return

        backup_dir = Path(getattr(settings, "DATA_BACKUP_DIR", settings.BASE_DIR.parent / "backups"))
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        output = (
            Path(options["output"])
            if options["output"]
            else backup_dir / f"kaleya-pgdump-{timestamp}.dump"
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        cmd = [
            "pg_dump",
            "--format=custom",
            "--compress=9",
            f"--host={db_host}",
            f"--port={db_port}",
            f"--username={db_user}",
            f"--dbname={db_name}",
            f"--file={output}",
        ]

        self.stdout.write(f"Running pg_dump for database '{db_name}' on {db_host}:{db_port} …")

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
        except FileNotFoundError:
            self.stderr.write(
                self.style.ERROR(
                    "pg_dump not found. Install postgresql-client on the server:\n"
                    "  apt-get install -y postgresql-client"
                )
            )
            return
        except subprocess.TimeoutExpired:
            self.stderr.write(self.style.ERROR("pg_dump timed out after 5 minutes."))
            return

        if result.returncode != 0:
            self.stderr.write(self.style.ERROR(f"pg_dump failed (exit {result.returncode}):\n{result.stderr}"))
            return

        size_mb = output.stat().st_size / 1_048_576
        self.stdout.write(self.style.SUCCESS(f"pg_dump saved: {output} ({size_mb:.2f} MB)"))
        self.stdout.write(
            f"To restore: pg_restore --clean --if-exists -h {db_host} -U {db_user} -d {db_name} {output}"
        )
