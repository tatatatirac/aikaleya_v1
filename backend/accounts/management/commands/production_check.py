from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Checks whether Kaleya has the minimum production configuration."

    def handle(self, *args, **options):
        errors = []
        warnings = []

        if settings.DEBUG:
            errors.append("DJANGO_DEBUG mora biti False na produkciji.")

        if settings.SECRET_KEY in {"dev-only-change-me", "change-this-secret-key", "change-this-to-a-long-random-secret-key"}:
            errors.append("DJANGO_SECRET_KEY mora biti pravi dugacak random secret key.")

        if not settings.ALLOWED_HOSTS or any(host in {"localhost", "127.0.0.1", "testserver"} for host in settings.ALLOWED_HOSTS):
            warnings.append("DJANGO_ALLOWED_HOSTS treba da sadrzi produkcioni domen, bez localhost vrednosti.")

        if not settings.CSRF_TRUSTED_ORIGINS:
            warnings.append("DJANGO_CSRF_TRUSTED_ORIGINS treba da sadrzi https domen produkcije.")

        default_db = settings.DATABASES["default"]
        if "sqlite3" in default_db.get("ENGINE", ""):
            errors.append("Produkcija treba da koristi PostgreSQL kroz DATABASE_URL, ne SQLite.")

        if settings.KALEYA_AI_PROVIDER == "anthropic" and not settings.KALEYA_ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY nije podesen.")

        if settings.KALEYA_AI_PROVIDER == "openai" and not settings.KALEYA_OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY nije podesen, a AI_PROVIDER je openai.")

        if not settings.KALEYA_ELEVENLABS_API_KEY:
            warnings.append("ELEVENLABS_API_KEY nije podesen. Glas nece raditi preko ElevenLabs.")

        if not settings.KALEYA_ELEVENLABS_VOICE_ID:
            warnings.append("ELEVENLABS_VOICE_ID nije podesen.")

        if settings.EMAIL_BACKEND.endswith("smtp.EmailBackend") and not settings.EMAIL_HOST:
            warnings.append("EMAIL_HOST nije podesen. Email potvrde i reset lozinke nece raditi.")

        if not getattr(settings, "DATA_BACKUP_DIR", None):
            warnings.append("DATA_BACKUP_DIR nije podesen. Backup komanda koristi podrazumevani lokalni folder.")

        demo_admin = User.objects.filter(username="admin@aikaleya.com").first()
        if demo_admin and demo_admin.check_password("admin123"):
            errors.append("Demo admin lozinka admin123 je jos aktivna. Na produkciji napravi novog admina ili promeni lozinku.")

        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"WARNING: {warning}"))

        if errors:
            for error in errors:
                self.stdout.write(self.style.ERROR(f"ERROR: {error}"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("Kaleya production check je prosao."))
