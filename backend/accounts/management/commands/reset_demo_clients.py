"""Wipe all demo BusinessClients (except the admin's), then create two
clean tenants:
  • Pro client     — blagojekosticrs@gmail.com
  • Starter client — 4mailbane@gmail.com

Admin user (bane@aikaleya.com) is preserved.

Usage:
  python backend/manage.py reset_demo_clients
  python backend/manage.py reset_demo_clients --pro-email X --starter-email Y --admin-email Z
"""

import secrets
import string

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import Plan
from clients.models import BusinessClient, ClientApiSettings


User = get_user_model()


DEFAULT_ADMIN_EMAIL = "bane@aikaleya.com"
DEFAULT_PRO_EMAIL = "blagojekosticrs@gmail.com"
DEFAULT_STARTER_EMAIL = "4mailbane@gmail.com"


def _generate_password(length: int = 14) -> str:
    """Generate a memorable password: 2 words + digits. Falls back to random."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Wipe demo tenants and create a clean Pro + Starter client (admin preserved)."

    def add_arguments(self, parser):
        parser.add_argument("--admin-email", default=DEFAULT_ADMIN_EMAIL)
        parser.add_argument("--pro-email", default=DEFAULT_PRO_EMAIL)
        parser.add_argument("--starter-email", default=DEFAULT_STARTER_EMAIL)
        parser.add_argument("--pro-business-name", default="Mike's Barbershop")
        parser.add_argument("--starter-business-name", default="Solo Beauty Studio")
        parser.add_argument(
            "--keep-existing-passwords",
            action="store_true",
            help="If a User already exists, don't reset its password.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        admin_email = opts["admin_email"].strip().lower()
        pro_email = opts["pro_email"].strip().lower()
        starter_email = opts["starter_email"].strip().lower()
        keep_passwords = opts["keep_existing_passwords"]

        self.stdout.write(self.style.WARNING("=" * 72))
        self.stdout.write(self.style.WARNING("WIPING all BusinessClients except the admin's"))
        self.stdout.write(self.style.WARNING("=" * 72))

        # ─── Step 1: Identify the admin user (keep) ──────────────────────────
        admin_user = (
            User.objects.filter(email__iexact=admin_email).first()
            or User.objects.filter(username__iexact=admin_email).first()
        )
        if not admin_user:
            self.stdout.write(self.style.WARNING(
                f"Admin user {admin_email} not found — leaving any 'god mode' admin alone."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f"Preserving admin: {admin_user.email or admin_user.username} (id {admin_user.id})"))

        # ─── Step 2: Wipe BusinessClients owned by anyone EXCEPT the admin ──
        preserved_admin_clients = []
        if admin_user:
            preserved_admin_clients = list(
                BusinessClient.objects.filter(owner=admin_user).values_list("id", flat=True)
            )

        to_delete = BusinessClient.objects.exclude(id__in=preserved_admin_clients)
        deleted_count = to_delete.count()
        self.stdout.write(f"Deleting {deleted_count} BusinessClients (cascade kills customers, appointments, conversations, integrations, etc).")
        to_delete.delete()

        # Also clean up orphan owner users (anyone whose only BC just got nuked)
        if admin_user:
            orphan_users = User.objects.exclude(id=admin_user.id).filter(
                business_clients__isnull=True,
                is_superuser=False,
                is_staff=False,
            )
        else:
            orphan_users = User.objects.filter(
                business_clients__isnull=True,
                is_superuser=False,
                is_staff=False,
            )
        # Don't kill the two emails we're about to (re)create
        orphan_users = orphan_users.exclude(email__iexact=pro_email).exclude(email__iexact=starter_email)
        orphan_count = orphan_users.count()
        if orphan_count:
            self.stdout.write(f"Deleting {orphan_count} orphan users with no business clients left.")
            orphan_users.delete()

        # ─── Step 3: Ensure billing plans exist ──────────────────────────────
        plans_by_code = {p.code: p for p in Plan.objects.all()}
        if Plan.CODE_BASIC not in plans_by_code or Plan.CODE_PRO not in plans_by_code:
            self.stdout.write(self.style.WARNING(
                "Plans missing — run `python manage.py seed_plans` first, then re-run this command."
            ))

        # ─── Step 4: Create Pro tenant ───────────────────────────────────────
        pro_password = self._upsert_tenant(
            email=pro_email,
            business_name=opts["pro_business_name"],
            package=BusinessClient.PACKAGE_PRO,
            language="en",
            keep_passwords=keep_passwords,
        )

        # ─── Step 5: Create Starter tenant ───────────────────────────────────
        starter_password = self._upsert_tenant(
            email=starter_email,
            business_name=opts["starter_business_name"],
            package=BusinessClient.PACKAGE_BASIC,
            language="en",
            keep_passwords=keep_passwords,
        )

        # ─── Final report ────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write(self.style.SUCCESS("DONE — fresh tenants created"))
        self.stdout.write(self.style.SUCCESS("=" * 72))
        self.stdout.write("")
        self.stdout.write(f"  PRO     · {pro_email}")
        if pro_password:
            self.stdout.write(self.style.SUCCESS(f"            password: {pro_password}"))
        else:
            self.stdout.write("            (existing password kept)")
        self.stdout.write(f"            business: {opts['pro_business_name']}")
        self.stdout.write("")
        self.stdout.write(f"  STARTER · {starter_email}")
        if starter_password:
            self.stdout.write(self.style.SUCCESS(f"            password: {starter_password}"))
        else:
            self.stdout.write("            (existing password kept)")
        self.stdout.write(f"            business: {opts['starter_business_name']}")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("⚠  Save these passwords now — they won't be shown again."))
        self.stdout.write("")

    def _upsert_tenant(self, *, email, business_name, package, language, keep_passwords):
        """Create or update a User + BusinessClient + ClientApiSettings.

        Returns the freshly-set password, or empty string if password unchanged.
        """
        user = User.objects.filter(email__iexact=email).first()
        new_password = ""

        if user:
            if not keep_passwords:
                new_password = _generate_password()
                user.set_password(new_password)
                user.email = email
                user.is_active = True
                user.save()
                self.stdout.write(f"  · Reset password for existing user {email}")
        else:
            new_password = _generate_password()
            username = email.split("@")[0][:30]
            user = User.objects.create_user(
                username=username,
                email=email,
                password=new_password,
                first_name=business_name.split()[0],
            )
            self.stdout.write(f"  · Created new user {email}")

        # Profile (for owner phone) — best-effort
        try:
            from accounts.models import Profile
            Profile.objects.get_or_create(user=user, defaults={"phone": ""})
        except Exception:
            pass

        # BusinessClient
        bc, created = BusinessClient.objects.update_or_create(
            owner=user,
            defaults={
                "name": business_name,
                "public_name": business_name,
                "package": package,
                "language": language,
                "interface_language": language,
                "voice_language": language,
                "timezone": "America/Los_Angeles",
                "is_demo": False,
                "kaleya_enabled": True,
            },
        )
        ClientApiSettings.objects.get_or_create(business_client=bc)
        self.stdout.write(
            f"  · {'Created' if created else 'Updated'} BusinessClient #{bc.id} "
            f"({business_name} / {package})"
        )

        return new_password
