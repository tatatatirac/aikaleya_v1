"""Delete per-call MP3 response directories older than N hours.

Each voice call writes turn audio under MEDIA_ROOT/voice/responses/{call_sid}/.
The voice pipeline intentionally does NOT delete these synchronously (Telnyx
fetches the MP3 AFTER our TeXML response, so deleting too early breaks the
caller's audio). This cron sweeps them after they're safely no longer needed.

Greetings under MEDIA_ROOT/voice/greetings/ are KEPT — they're cached and
reused across calls for the same salon+language.

Usage:
  python manage.py cleanup_voice_audio                  # default 24h
  python manage.py cleanup_voice_audio --older-than 6   # 6h
  python manage.py cleanup_voice_audio --dry-run

Recommended cron:
  0 * * * * cd /var/www/aikaleya && .venv/bin/python backend/manage.py cleanup_voice_audio >> /var/log/kaleya_audio_cleanup.log 2>&1
"""

import shutil
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete per-call voice MP3 directories older than --older-than hours (default 24)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--older-than", type=int, default=24,
            help="Delete call dirs whose mtime is older than this many hours (default 24).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **opts):
        hours = max(1, int(opts["older_than"]))
        cutoff = time.time() - (hours * 3600)
        dry = opts["dry_run"]

        base = Path(settings.MEDIA_ROOT) / "voice" / "responses"
        if not base.exists():
            self.stdout.write("Nothing to do — voice/responses/ does not exist.")
            return

        removed = 0
        kept = 0
        bytes_freed = 0

        for call_dir in base.iterdir():
            if not call_dir.is_dir():
                continue
            try:
                mtime = call_dir.stat().st_mtime
            except OSError:
                continue
            if mtime >= cutoff:
                kept += 1
                continue

            size = 0
            for f in call_dir.rglob("*"):
                if f.is_file():
                    try:
                        size += f.stat().st_size
                    except OSError:
                        pass

            if dry:
                self.stdout.write(f"[DRY] would remove {call_dir.name} ({size // 1024} KB)")
            else:
                try:
                    shutil.rmtree(call_dir, ignore_errors=True)
                except Exception as exc:
                    self.stderr.write(f"Failed to remove {call_dir}: {exc}")
                    continue

            removed += 1
            bytes_freed += size

        verb = "Would remove" if dry else "Removed"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {removed} call dir(s) (~{bytes_freed // 1024} KB freed). Kept {kept} recent dir(s)."
        ))
