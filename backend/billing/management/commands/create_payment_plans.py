import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from billing.models import Plan


PLAN_ENV_KEYS = {
    Plan.CODE_BASIC: "PAYPAL_PLAN_BASIC",
    Plan.CODE_PRO: "PAYPAL_PLAN_PRO",
    Plan.CODE_BUSINESS: "PAYPAL_PLAN_BUSINESS",
    Plan.CODE_BUSINESS_PLUS: "PAYPAL_PLAN_BUSINESS_PLUS",
}


class Command(BaseCommand):
    help = "Creates sandbox recurring payment plans for Kaleya packages and optionally writes their IDs to .env."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-env",
            action="store_true",
            help="Write created plan IDs into the local .env file.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create new plans even if a plan ID already exists in settings.",
        )
        parser.add_argument(
            "--env-file",
            default=str(settings.PROJECT_ROOT / ".env"),
            help="Path to the .env file that should receive plan IDs.",
        )

    def handle(self, *args, **options):
        self._validate_settings()

        created = {}
        for plan in self._plans():
            env_key = PLAN_ENV_KEYS[plan.code]
            existing_id = settings.KALEYA_PAYPAL_PLAN_IDS.get(plan.code, "")
            if existing_id and not options["force"]:
                self.stdout.write(f"{plan.name}: already configured as {existing_id}")
                created[env_key] = existing_id
                continue

            product = self._create_product(plan)
            payment_plan = self._create_plan(plan, product["id"])
            created[env_key] = payment_plan["id"]
            self.stdout.write(self.style.SUCCESS(f"{plan.name}: {payment_plan['id']}"))

        if options["write_env"]:
            self._write_env(options["env_file"], created)
            self.stdout.write(self.style.SUCCESS(f"Plan IDs written to {options['env_file']}"))
        else:
            self.stdout.write("")
            self.stdout.write("Copy these values into .env:")
            for key, value in created.items():
                self.stdout.write(f"{key}={value}")

    def _validate_settings(self):
        if settings.KALEYA_PAYPAL_ENVIRONMENT != "sandbox":
            raise CommandError("This command is intended for sandbox first. Set PAYPAL_ENVIRONMENT=sandbox.")
        if not settings.KALEYA_PAYPAL_CLIENT_ID or not settings.KALEYA_PAYPAL_CLIENT_SECRET:
            raise CommandError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be configured in .env.")

    def _plans(self):
        plans = list(
            Plan.objects.filter(code__in=PLAN_ENV_KEYS.keys(), active=True)
            .exclude(is_contact_only=True)
            .order_by("sort_order")
        )
        if not plans:
            raise CommandError("No active Kaleya paid plans found. Run: python backend\\manage.py seed_plans")
        return plans

    def _api_base(self):
        return "https://api-m.sandbox.paypal.com"

    def _access_token(self):
        credentials = f"{settings.KALEYA_PAYPAL_CLIENT_ID}:{settings.KALEYA_PAYPAL_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        form = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = urllib.request.Request(
            f"{self._api_base()}/v1/oauth2/token",
            data=form,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CommandError(self._http_error_message(exc)) from exc
        token = data.get("access_token", "")
        if not token:
            raise CommandError("Payment provider did not return an access token.")
        return token

    def _json_request(self, path, payload):
        token = self._access_token()
        request = urllib.request.Request(
            f"{self._api_base()}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CommandError(self._http_error_message(exc)) from exc

    def _create_product(self, plan):
        payload = {
            "name": f"Kaleya {plan.name}",
            "description": plan.description or f"Kaleya {plan.name} subscription",
            "type": "SERVICE",
            "category": "SOFTWARE",
        }
        return self._json_request("/v1/catalogs/products", payload)

    def _create_plan(self, plan, product_id):
        billing_cycles = []
        if plan.trial_days:
            billing_cycles.append(
                {
                    "frequency": {
                        "interval_unit": "DAY",
                        "interval_count": int(plan.trial_days),
                    },
                    "tenure_type": "TRIAL",
                    "sequence": 1,
                    "total_cycles": 1,
                }
            )

        regular_sequence = 2 if billing_cycles else 1
        billing_cycles.append(
            {
                "frequency": {"interval_unit": "MONTH", "interval_count": 1},
                "tenure_type": "REGULAR",
                "sequence": regular_sequence,
                "total_cycles": 0,
                "pricing_scheme": {
                    "fixed_price": {
                        "value": self._money(plan.monthly_price),
                        "currency_code": plan.currency,
                    }
                },
            }
        )

        payload = {
            "product_id": product_id,
            "name": f"Kaleya {plan.name}",
            "description": plan.description or f"Kaleya {plan.name} monthly plan",
            "status": "ACTIVE",
            "billing_cycles": billing_cycles,
            "payment_preferences": {
                "auto_bill_outstanding": True,
                "setup_fee_failure_action": "CONTINUE",
                "payment_failure_threshold": 3,
            },
            "taxes": {"percentage": "0", "inclusive": False},
        }
        return self._json_request("/v1/billing/plans", payload)

    def _money(self, value):
        amount = Decimal(value).quantize(Decimal("0.01"))
        return f"{amount:.2f}"

    def _http_error_message(self, exc):
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = ""
        return f"Payment API error {exc.code}: {body or exc.reason}"

    def _write_env(self, env_file, values):
        path = settings.PROJECT_ROOT / ".env" if not env_file else env_file
        path = str(path)
        existing_lines = []
        try:
            with open(path, "r", encoding="utf-8") as handle:
                existing_lines = handle.readlines()
        except FileNotFoundError:
            existing_lines = []

        remaining = dict(values)
        output = []
        for line in existing_lines:
            stripped = line.strip()
            if "=" in stripped and not stripped.startswith("#"):
                key = stripped.split("=", 1)[0].strip()
                if key in remaining:
                    output.append(f"{key}={remaining.pop(key)}\n")
                    continue
            output.append(line)

        if remaining:
            if output and not output[-1].endswith("\n"):
                output[-1] = f"{output[-1]}\n"
            output.append("\n")
            output.append("# Payment plan IDs\n")
            for key, value in remaining.items():
                output.append(f"{key}={value}\n")

        with open(path, "w", encoding="utf-8") as handle:
            handle.writelines(output)
