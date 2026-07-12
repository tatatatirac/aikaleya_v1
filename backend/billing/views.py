import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, user_role
from billing.models import CheckoutSession, PaymentWebhookEvent, PendingCheckoutRegistration, Plan, Subscription
from billing.serializers import (
    CheckoutSessionCreateSerializer,
    CheckoutSessionSerializer,
    PaymentWebhookEventSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from billing.services import (
    activate_checkout_subscription,
    cancel_checkout_subscription,
    entitlements_for_client,
    mark_checkout_subscription_past_due,
    plan_for_client,
    subscription_state_for_client,
)
from clients.models import BusinessClient, get_active_client_for_user


PAYPAL_ACTIVE_EVENTS = {
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.RE-ACTIVATED",
    "PAYMENT.SALE.COMPLETED",
}

PAYPAL_CANCELLED_EVENTS = {
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.EXPIRED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "PAYMENT.SALE.DENIED",
    "PAYMENT.SALE.REFUNDED",
    "PAYMENT.SALE.REVERSED",
}

LEMONSQUEEZY_ACTIVE_EVENTS = {
    "subscription_created",
    "subscription_resumed",
    "subscription_payment_success",
}

LEMONSQUEEZY_PAST_DUE_EVENTS = {
    "subscription_payment_failed",
}

LEMONSQUEEZY_CANCELLED_EVENTS = {
    "subscription_cancelled",
    "subscription_expired",
    "subscription_paused",
}


def append_url_query(url, **params):
    split = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(split.query, keep_blank_values=True))
    query.update({key: str(value) for key, value in params.items() if value not in ("", None)})
    return urllib.parse.urlunsplit(
        (
            split.scheme,
            split.netloc,
            split.path,
            urllib.parse.urlencode(query),
            split.fragment,
        )
    )


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsAdminRole()]

    def get_queryset(self):
        return Plan.objects.filter(active=True)


class PaymentWebhookEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PaymentWebhookEventSerializer
    permission_classes = (IsAdminRole,)

    def get_queryset(self):
        return PaymentWebhookEvent.objects.select_related("checkout", "checkout__plan").all()


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_client(self):
        if user_role(self.request.user) == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                return BusinessClient.objects.get(id=client_id)
            return BusinessClient.objects.first()
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return Subscription.objects.none()
        return Subscription.objects.select_related("plan").filter(business_client=client)

    def perform_create(self, serializer):
        plan = Plan.objects.get(id=serializer.validated_data.pop("plan_id"))
        serializer.save(business_client=self.get_client(), plan=plan)

    @action(detail=False, methods=["get"], url_path="entitlements")
    def entitlements(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        plan = plan_for_client(client)
        return Response(
            {
                "package": client.package,
                "plan": {
                    "code": plan.code if plan else client.package,
                    "name": plan.name if plan else client.get_package_display(),
                },
                "entitlements": entitlements_for_client(client),
                "subscription": subscription_state_for_client(client),
            }
        )

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        return Response(
            {
                "package": client.package,
                "subscription": subscription_state_for_client(client),
            }
        )


class CheckoutSessionViewSet(viewsets.ModelViewSet):
    serializer_class = CheckoutSessionSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return CheckoutSession.objects.none()
        if user_role(self.request.user) == "admin":
            return CheckoutSession.objects.select_related("plan", "business_client")
        client = get_active_client_for_user(self.request.user)
        if not client:
            return CheckoutSession.objects.none()
        return CheckoutSession.objects.select_related("plan", "business_client").filter(business_client=client)

    def create(self, request, *args, **kwargs):
        input_serializer = CheckoutSessionCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        payload = input_serializer.validated_data
        raw_plan_code = payload["plan_code"]  # e.g. "basic" or "basic_yearly"
        billing_period = "yearly" if raw_plan_code.endswith("_yearly") else "monthly"
        db_plan_code = raw_plan_code[:-7] if billing_period == "yearly" else raw_plan_code
        plan = Plan.objects.filter(code=db_plan_code, active=True).first()
        if not plan:
            return Response({"detail": "Paket nije pronadjen."}, status=status.HTTP_400_BAD_REQUEST)
        if payload.get("email"):
            existing_user = (
                User.objects.filter(email__iexact=payload.get("email", "")).first()
                or User.objects.filter(username__iexact=payload.get("email", "")).first()
            )
            # Browse-only accounts (e.g. Google sign-up, no subscription yet) MAY
            # check out — the webhook attaches and activates their existing client.
            # Only block emails that already have an active subscription.
            if existing_user and Subscription.objects.filter(
                business_client__owner=existing_user, status=Subscription.STATUS_ACTIVE
            ).exists():
                return Response(
                    {"email": ["Nalog sa ovim emailom vec ima aktivnu pretplatu."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        metadata = {
            "plan_code": db_plan_code,
            "billing_period": billing_period,
            "note": payload.get("note", ""),
            "source": "kaleya_frontend",
        }
        yearly_amount = plan.monthly_price * 10  # 2 months free = 10× monthly
        amount = yearly_amount if billing_period == "yearly" else plan.monthly_price
        checkout = CheckoutSession.objects.create(
            plan=plan,
            provider=CheckoutSession.PROVIDER_MANUAL,
            status=CheckoutSession.STATUS_MANUAL_CONTACT,
            email=payload.get("email", ""),
            company=payload.get("company", ""),
            full_name=payload.get("full_name", ""),
            amount=amount,
            currency=plan.currency,
            trial_days=plan.trial_days,
            metadata=metadata,
        )
        if payload.get("email"):
            PendingCheckoutRegistration.objects.update_or_create(
                checkout=checkout,
                defaults={
                    "email": payload.get("email", "").strip().lower(),
                    "company": payload.get("company", "").strip(),
                    "full_name": payload.get("full_name", "").strip(),
                    "password_hash": "",  # password is no longer set at checkout — set via /setup/ email link
                    "phone": payload.get("phone", "").strip(),
                    "country": payload.get("country", "").strip(),
                },
            )

        payment_provider_configured = self._payment_provider_is_configured(plan, raw_plan_code=raw_plan_code)
        message = "Payment provider jos nije povezan. Zahtev je sacuvan za rucni kontakt."

        if plan.is_contact_only:
            message = "Ovaj paket ide kroz direktan kontakt i dogovor."
        elif settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_LEMONSQUEEZY:
            if payment_provider_configured:
                lemon_session, lemon_message = self._create_lemonsqueezy_checkout(plan, payload, metadata, checkout)
                if lemon_session:
                    checkout.provider = CheckoutSession.PROVIDER_LEMONSQUEEZY
                    checkout.status = CheckoutSession.STATUS_PROVIDER_PENDING
                    checkout.checkout_url = lemon_session["checkout_url"]
                    checkout.external_checkout_id = lemon_session["id"]
                    checkout.metadata = {
                        **checkout.metadata,
                        "checkout_public_id": str(checkout.public_id),
                        "lemonsqueezy_variant_id": settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.get(plan.code, ""),
                    }
                    checkout.save(
                        update_fields=[
                            "provider",
                            "status",
                            "checkout_url",
                            "external_checkout_id",
                            "metadata",
                            "updated_at",
                        ]
                    )
                    message = "Lemon Squeezy checkout je kreiran."
                else:
                    message = lemon_message
            else:
                message = "Lemon Squeezy jos nije podesen. Zahtev je sacuvan za rucni kontakt."
        elif settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_PAYPAL:
            if payment_provider_configured:
                paypal_session, paypal_message = self._create_paypal_checkout(plan, payload, metadata)
                if paypal_session:
                    checkout.provider = CheckoutSession.PROVIDER_PAYPAL
                    checkout.status = CheckoutSession.STATUS_PROVIDER_PENDING
                    checkout.checkout_url = paypal_session["checkout_url"]
                    checkout.external_checkout_id = paypal_session["id"]
                    checkout.save(update_fields=["provider", "status", "checkout_url", "external_checkout_id", "updated_at"])
                    message = "PayPal checkout je kreiran."
                else:
                    message = paypal_message
            else:
                message = "PayPal jos nije podesen. Zahtev je sacuvan za rucni kontakt."
        elif payment_provider_configured:
            stripe_session, stripe_message = self._create_stripe_checkout(plan, payload, metadata)
            if stripe_session:
                checkout.provider = CheckoutSession.PROVIDER_STRIPE
                checkout.status = CheckoutSession.STATUS_PROVIDER_PENDING
                checkout.checkout_url = getattr(stripe_session, "url", "") or stripe_session.get("url", "")
                checkout.external_checkout_id = getattr(stripe_session, "id", "") or stripe_session.get("id", "")
                checkout.save(update_fields=["provider", "status", "checkout_url", "external_checkout_id", "updated_at"])
                message = "Stripe checkout je kreiran."
            else:
                message = stripe_message

        data = dict(CheckoutSessionSerializer(checkout).data)
        data["message"] = message
        data["payment_provider_configured"] = payment_provider_configured
        data["local_checkout_url"] = f"/checkout.html?session={checkout.public_id}" if not plan.is_contact_only else ""
        return Response(data, status=status.HTTP_201_CREATED)

    def _payment_provider_is_configured(self, plan, raw_plan_code=None):
        if settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_LEMONSQUEEZY:
            return self._lemonsqueezy_is_configured(plan, raw_plan_code=raw_plan_code)
        if settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_PAYPAL:
            return self._paypal_is_configured(plan)
        if settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_STRIPE:
            return self._stripe_is_configured(plan)
        return False

    def _lemonsqueezy_is_configured(self, plan, raw_plan_code=None):
        variant_id = (
            settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.get(raw_plan_code or plan.code)
            or settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.get(plan.code)
        )
        return bool(
            settings.KALEYA_LEMONSQUEEZY_API_KEY
            and settings.KALEYA_LEMONSQUEEZY_STORE_ID
            and variant_id
        )

    def _lemonsqueezy_json_request(self, url, payload):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.KALEYA_LEMONSQUEEZY_API_KEY}",
                "Content-Type": "application/vnd.api+json",
                "Accept": "application/vnd.api+json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))

    def _lemonsqueezy_error_message(self, exc):
        if isinstance(exc, urllib.error.HTTPError):
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            return f"Lemon Squeezy greska {exc.code}: {body or exc.reason}"
        return f"Lemon Squeezy greska: {exc}"

    def _create_lemonsqueezy_checkout(self, plan, payload, metadata, checkout):
        billing_period = metadata.get("billing_period", "monthly")
        raw_plan_code = f"{plan.code}_yearly" if billing_period == "yearly" else plan.code
        variant_id = (
            settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.get(raw_plan_code)
            or settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.get(plan.code, "")
        )
        success_url = append_url_query(
            settings.KALEYA_PAYMENT_SUCCESS_URL,
            payment="success",
            checkout=str(checkout.public_id),
        )
        custom_data = {
            "checkout_public_id": str(checkout.public_id),
            "plan_code": plan.code,
            "billing_period": billing_period,
            "source": "kaleya_frontend",
        }
        note = metadata.get("note")
        if note:
            custom_data["note"] = str(note)

        checkout_data = {"custom": custom_data}
        if payload.get("email"):
            checkout_data["email"] = payload["email"]
        if payload.get("full_name"):
            checkout_data["name"] = payload["full_name"]

        if billing_period == "yearly":
            yearly_total = int(plan.monthly_price * 10)
            billing_desc = f"{plan.trial_days} days trial, then {yearly_total} {plan.currency} per year."
        else:
            billing_desc = f"{plan.trial_days} days trial, then {plan.monthly_price} {plan.currency} per month."

        lemon_payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "product_options": {
                        "name": f"Kaleya {plan.name}",
                        "description": billing_desc,
                        "redirect_url": success_url,
                        "receipt_button_text": "Open Kaleya",
                        "receipt_link_url": success_url,
                        "enabled_variants": [int(variant_id)] if str(variant_id).isdigit() else [variant_id],
                    },
                    "checkout_options": {
                        "embed": False,
                        "media": False,
                        "logo": False,
                        "desc": False,
                        "discount": False,
                        "dark": True,
                    },
                    "checkout_data": checkout_data,
                    "test_mode": settings.KALEYA_LEMONSQUEEZY_TEST_MODE,
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": str(settings.KALEYA_LEMONSQUEEZY_STORE_ID),
                        }
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": str(variant_id),
                        }
                    },
                },
            }
        }

        try:
            lemon_data = self._lemonsqueezy_json_request(
                f"{settings.KALEYA_LEMONSQUEEZY_API_BASE}/v1/checkouts",
                lemon_payload,
            )
        except Exception as exc:
            return None, self._lemonsqueezy_error_message(exc)

        data = lemon_data.get("data") or {}
        attributes = data.get("attributes") or {}
        checkout_url = attributes.get("url", "")
        if not checkout_url:
            return None, "Lemon Squeezy nije vratio checkout link."
        return {"id": str(data.get("id", "")), "checkout_url": checkout_url}, ""

    def _paypal_is_configured(self, plan):
        return bool(
            settings.KALEYA_PAYPAL_CLIENT_ID
            and settings.KALEYA_PAYPAL_CLIENT_SECRET
            and settings.KALEYA_PAYPAL_PLAN_IDS.get(plan.code)
        )

    def _paypal_api_base(self):
        if settings.KALEYA_PAYPAL_ENVIRONMENT == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    def _paypal_json_request(self, url, token, payload):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))

    def _paypal_access_token(self):
        credentials = f"{settings.KALEYA_PAYPAL_CLIENT_ID}:{settings.KALEYA_PAYPAL_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        form = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = urllib.request.Request(
            f"{self._paypal_api_base()}/v1/oauth2/token",
            data=form,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("access_token", "")

    def _paypal_error_message(self, exc):
        if isinstance(exc, urllib.error.HTTPError):
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            return f"PayPal greska {exc.code}: {body or exc.reason}"
        return f"PayPal greska: {exc}"

    def _paypal_subscriber(self, payload):
        subscriber = {}
        email = payload.get("email")
        if email:
            subscriber["email_address"] = email
        full_name = (payload.get("full_name") or "").strip()
        if full_name:
            parts = full_name.split()
            subscriber["name"] = {
                "given_name": parts[0],
                "surname": " ".join(parts[1:]) if len(parts) > 1 else parts[0],
            }
        return subscriber

    def _create_paypal_checkout(self, plan, payload, metadata):
        try:
            token = self._paypal_access_token()
            if not token:
                return None, "PayPal nije vratio access token."
            paypal_metadata = {key: str(value) for key, value in metadata.items() if value is not None}
            subscription_payload = {
                "plan_id": settings.KALEYA_PAYPAL_PLAN_IDS[plan.code],
                "custom_id": json.dumps(paypal_metadata, separators=(",", ":"))[:127],
                "application_context": {
                    "brand_name": "Kaleya",
                    "locale": "en-US",
                    "shipping_preference": "NO_SHIPPING",
                    "user_action": "SUBSCRIBE_NOW",
                    "return_url": settings.KALEYA_PAYMENT_SUCCESS_URL,
                    "cancel_url": settings.KALEYA_PAYMENT_CANCEL_URL,
                },
            }
            subscriber = self._paypal_subscriber(payload)
            if subscriber:
                subscription_payload["subscriber"] = subscriber

            paypal_data = self._paypal_json_request(
                f"{self._paypal_api_base()}/v1/billing/subscriptions",
                token,
                subscription_payload,
            )
        except Exception as exc:
            return None, self._paypal_error_message(exc)

        approval_url = ""
        for link in paypal_data.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link.get("href", "")
                break
        if not approval_url:
            return None, "PayPal nije vratio approval link za korisnika."
        return {"id": paypal_data.get("id", ""), "checkout_url": approval_url}, ""

    def _stripe_is_configured(self, plan):
        return bool(
            settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_STRIPE
            and settings.KALEYA_STRIPE_SECRET_KEY
            and settings.KALEYA_STRIPE_PRICE_IDS.get(plan.code)
        )

    def _create_stripe_checkout(self, plan, payload, metadata):
        try:
            import stripe
        except ImportError:
            return None, "Stripe Python paket nije instaliran. Instalirajte requirements.txt na serveru."

        stripe.api_key = settings.KALEYA_STRIPE_SECRET_KEY
        stripe_metadata = {key: str(value) for key, value in metadata.items() if value is not None}
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                success_url=settings.KALEYA_PAYMENT_SUCCESS_URL,
                cancel_url=settings.KALEYA_PAYMENT_CANCEL_URL,
                customer_email=payload.get("email") or None,
                line_items=[
                    {
                        "price": settings.KALEYA_STRIPE_PRICE_IDS[plan.code],
                        "quantity": 1,
                    }
                ],
                subscription_data={
                    "trial_period_days": plan.trial_days,
                    "metadata": stripe_metadata,
                },
                metadata=stripe_metadata,
            )
        except Exception as exc:
            return None, f"Stripe checkout nije kreiran: {exc}"
        return session, ""


class PayPalPublicConfigView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        provider = settings.KALEYA_PAYMENT_PROVIDER
        if provider == CheckoutSession.PROVIDER_LEMONSQUEEZY:
            plans_configured = {
                code: bool(variant_id)
                for code, variant_id in settings.KALEYA_LEMONSQUEEZY_VARIANT_IDS.items()
            }
            provider_configured = bool(
                settings.KALEYA_LEMONSQUEEZY_API_KEY
                and settings.KALEYA_LEMONSQUEEZY_STORE_ID
            )
            ready = bool(
                provider_configured
                and any(plans_configured.values())
            )
            environment = "test" if settings.KALEYA_LEMONSQUEEZY_TEST_MODE else "live"
            return Response(
                {
                    "provider": provider,
                    "environment": environment,
                    "client_id": "",
                    "client_id_configured": provider_configured,
                    "webhook_configured": bool(settings.KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET),
                    "plans_configured": plans_configured,
                    "ready": ready,
                }
            )

        if provider == CheckoutSession.PROVIDER_PAYPAL:
            plans_configured = {
                code: bool(plan_id)
                for code, plan_id in settings.KALEYA_PAYPAL_PLAN_IDS.items()
            }
            client_id = settings.KALEYA_PAYPAL_CLIENT_ID
            ready = bool(
                provider == CheckoutSession.PROVIDER_PAYPAL
                and client_id
                and settings.KALEYA_PAYPAL_CLIENT_SECRET
                and any(plans_configured.values())
            )
            return Response(
                {
                    "provider": provider,
                    "environment": settings.KALEYA_PAYPAL_ENVIRONMENT,
                    "client_id": client_id if client_id else "",
                    "client_id_configured": bool(client_id),
                    "webhook_configured": bool(settings.KALEYA_PAYPAL_WEBHOOK_ID),
                    "plans_configured": plans_configured,
                    "ready": ready,
                }
            )

        plans_configured = {
            code: bool(price_id)
            for code, price_id in settings.KALEYA_STRIPE_PRICE_IDS.items()
        }
        ready = bool(
            provider == CheckoutSession.PROVIDER_STRIPE
            and settings.KALEYA_STRIPE_SECRET_KEY
            and any(plans_configured.values())
        )
        return Response(
            {
                "provider": provider,
                "environment": "manual" if provider == CheckoutSession.PROVIDER_MANUAL else "live",
                "client_id": "",
                "client_id_configured": False,
                "webhook_configured": bool(settings.KALEYA_STRIPE_WEBHOOK_SECRET),
                "plans_configured": plans_configured,
                "ready": ready,
            }
        )


class CheckoutPublicDetailView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request, public_id):
        checkout = (
            CheckoutSession.objects.select_related("plan", "business_client")
            .filter(public_id=public_id)
            .first()
        )
        if not checkout:
            return Response({"detail": "Checkout sesija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)
        subscription = None
        if checkout.business_client_id:
            subscription = Subscription.objects.filter(business_client=checkout.business_client).first()
        return Response(
            {
                "public_id": str(checkout.public_id),
                "provider": checkout.provider,
                "status": checkout.status,
                "plan": {
                    "code": checkout.plan.code,
                    "name": checkout.plan.name,
                    "trial_days": checkout.plan.trial_days,
                },
                "amount": checkout.amount,
                "currency": checkout.currency,
                "trial_days": checkout.trial_days,
                "provider_checkout_url": checkout.checkout_url
                if checkout.status == CheckoutSession.STATUS_PROVIDER_PENDING
                else "",
                "payment_ready": bool(
                    checkout.checkout_url
                    and checkout.status == CheckoutSession.STATUS_PROVIDER_PENDING
                ),
                "account_activated": bool(checkout.business_client_id),
                "subscription_status": subscription.status if subscription else "",
                "login_url": "/",
            }
        )


class LemonSqueezyWebhookView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        raw_body = getattr(getattr(request, "_request", request), "body", b"")
        raw_body_text = raw_body.decode("utf-8", errors="replace") if raw_body else ""
        webhook_log = None
        try:
            event = json.loads(raw_body.decode("utf-8")) if raw_body else request.data
        except (json.JSONDecodeError, UnicodeDecodeError):
            webhook_log = PaymentWebhookEvent.objects.create(
                provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
                status=PaymentWebhookEvent.STATUS_FAILED,
                raw_body=raw_body_text,
                error="Neispravan Lemon Squeezy webhook JSON.",
            )
            return Response({"detail": "Neispravan Lemon Squeezy webhook JSON."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(event, dict):
            webhook_log = PaymentWebhookEvent.objects.create(
                provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
                status=PaymentWebhookEvent.STATUS_FAILED,
                raw_body=raw_body_text,
                payload={"received_type": type(event).__name__},
                error="Lemon Squeezy webhook mora biti JSON objekat.",
            )
            return Response({"detail": "Lemon Squeezy webhook mora biti JSON objekat."}, status=status.HTTP_400_BAD_REQUEST)

        meta = event.get("meta") or {}
        data = event.get("data") or {}
        attributes = data.get("attributes") or {}
        event_name = meta.get("event_name", "")
        external_id = str(data.get("id") or attributes.get("subscription_id") or "")
        external_event_id = str(meta.get("webhook_id") or meta.get("event_id") or "")
        webhook_log = PaymentWebhookEvent.objects.create(
            provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
            event_name=event_name,
            external_event_id=external_event_id,
            external_object_id=external_id,
            status=PaymentWebhookEvent.STATUS_RECEIVED,
            raw_body=raw_body_text,
            payload=event,
        )

        verified, verify_error = self._verify_lemonsqueezy_signature(request, raw_body)
        if not verified:
            webhook_log.status = PaymentWebhookEvent.STATUS_FAILED
            webhook_log.error = verify_error
            webhook_log.save(update_fields=["status", "error", "updated_at"])
            return Response({"detail": verify_error}, status=status.HTTP_400_BAD_REQUEST)

        webhook_log.signature_valid = True
        webhook_log.status = PaymentWebhookEvent.STATUS_VERIFIED
        checkout = self._checkout_for_event(meta, external_id)
        webhook_log.checkout = checkout
        webhook_log.save(update_fields=["signature_valid", "status", "checkout", "updated_at"])

        try:
            if checkout and event_name in LEMONSQUEEZY_ACTIVE_EVENTS:
                checkout.status = CheckoutSession.STATUS_PAID
                checkout.external_checkout_id = external_id or checkout.external_checkout_id
                checkout.metadata = {**checkout.metadata, "last_lemonsqueezy_event": event_name}
                checkout.save(update_fields=["status", "external_checkout_id", "metadata", "updated_at"])
                self._activate_subscription(checkout, attributes)
                webhook_log.status = PaymentWebhookEvent.STATUS_PROCESSED
                webhook_log.processed_at = timezone.now()
            elif checkout and event_name in LEMONSQUEEZY_PAST_DUE_EVENTS:
                checkout.metadata = {**checkout.metadata, "last_lemonsqueezy_event": event_name}
                checkout.save(update_fields=["metadata", "updated_at"])
                self._mark_subscription_past_due(checkout, attributes)
                webhook_log.status = PaymentWebhookEvent.STATUS_PROCESSED
                webhook_log.processed_at = timezone.now()
            elif checkout and event_name in LEMONSQUEEZY_CANCELLED_EVENTS:
                checkout.status = CheckoutSession.STATUS_CANCELLED
                checkout.external_checkout_id = external_id or checkout.external_checkout_id
                checkout.metadata = {**checkout.metadata, "last_lemonsqueezy_event": event_name}
                checkout.save(update_fields=["status", "external_checkout_id", "metadata", "updated_at"])
                self._cancel_subscription(checkout, attributes)
                webhook_log.status = PaymentWebhookEvent.STATUS_PROCESSED
                webhook_log.processed_at = timezone.now()
            else:
                webhook_log.status = PaymentWebhookEvent.STATUS_IGNORED
                webhook_log.error = "" if checkout else "Checkout sesija nije pronadjena za webhook."
            webhook_log.save(update_fields=["status", "processed_at", "error", "updated_at"])
        except Exception as exc:
            webhook_log.status = PaymentWebhookEvent.STATUS_FAILED
            webhook_log.error = str(exc)
            webhook_log.save(update_fields=["status", "error", "updated_at"])
            raise

        return Response(
            {
                "received": True,
                "verified": True,
                "webhook_event_id": webhook_log.id,
                "webhook_event_status": webhook_log.status,
                "event_name": event_name,
                "external_subscription_id": external_id,
                "checkout_found": bool(checkout),
            }
        )

    def _verify_lemonsqueezy_signature(self, request, raw_body):
        secret = settings.KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET
        if settings.DEBUG and not secret:
            return True, ""
        if not secret:
            return False, "LEMONSQUEEZY_WEBHOOK_SECRET nije podesen u .env fajlu."
        signature = request.headers.get("X-Signature", "")
        if not signature:
            return False, "Lemon Squeezy webhook potpis nedostaje."
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        if hmac.compare_digest(expected, signature):
            return True, ""
        return False, "Lemon Squeezy webhook potpis nije validan."

    def _checkout_for_event(self, meta, external_id):
        custom_data = meta.get("custom_data") or {}
        checkout_public_id = (
            custom_data.get("checkout_public_id")
            or custom_data.get("checkout_session_public_id")
            or custom_data.get("checkout")
        )
        query = CheckoutSession.objects.select_related("plan", "business_client")
        if checkout_public_id:
            checkout = query.filter(public_id=checkout_public_id).first()
            if checkout:
                return checkout
        if external_id:
            return query.filter(external_checkout_id=external_id).first()
        return None

    def _activate_subscription(self, checkout, attributes):
        # Save the Lemon Squeezy customer portal URL in checkout metadata so the
        # owner can self-serve (cancel, update payment) without contacting support.
        urls = attributes.get("urls") or {}
        portal_url = urls.get("customer_portal", "")
        if portal_url:
            md = dict(checkout.metadata or {})
            md["customer_portal_url"] = portal_url
            checkout.metadata = md
            checkout.save(update_fields=["metadata", "updated_at"])

        return activate_checkout_subscription(
            checkout,
            external_customer_id=str(attributes.get("customer_id") or ""),
            external_subscription_id=checkout.external_checkout_id,
            trial_ends_at=attributes.get("trial_ends_at"),
            current_period_start=attributes.get("created_at"),
            current_period_end=attributes.get("renews_at") or attributes.get("ends_at"),
        )

    def _mark_subscription_past_due(self, checkout, attributes):
        return mark_checkout_subscription_past_due(
            checkout,
            external_customer_id=str(attributes.get("customer_id") or ""),
            external_subscription_id=checkout.external_checkout_id,
        )

    def _cancel_subscription(self, checkout, attributes):
        return cancel_checkout_subscription(
            checkout,
            external_customer_id=str(attributes.get("customer_id") or ""),
            external_subscription_id=checkout.external_checkout_id,
        )


class PayPalWebhookView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        try:
            raw_body = getattr(getattr(request, "_request", request), "body", b"")
            event = json.loads(raw_body.decode("utf-8")) if raw_body else request.data
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response({"detail": "Neispravan PayPal webhook JSON."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(event, dict):
            return Response({"detail": "PayPal webhook mora biti JSON objekat."}, status=status.HTTP_400_BAD_REQUEST)

        verified, verify_error = self._verify_paypal_signature(request, event)
        if not verified:
            return Response({"detail": verify_error}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get("event_type", "")
        resource = event.get("resource") or {}
        external_id = self._external_subscription_id(resource)
        checkout = self._checkout_for_external_id(external_id)

        if checkout and event_type in PAYPAL_ACTIVE_EVENTS:
            checkout.status = CheckoutSession.STATUS_PAID
            checkout.metadata = {**checkout.metadata, "last_paypal_event": event_type}
            checkout.save(update_fields=["status", "metadata", "updated_at"])
            self._activate_subscription(checkout)
        elif checkout and event_type in PAYPAL_CANCELLED_EVENTS:
            checkout.status = CheckoutSession.STATUS_CANCELLED
            checkout.metadata = {**checkout.metadata, "last_paypal_event": event_type}
            checkout.save(update_fields=["status", "metadata", "updated_at"])
            self._cancel_subscription(checkout)

        return Response(
            {
                "received": True,
                "verified": True,
                "event_type": event_type,
                "external_subscription_id": external_id,
                "checkout_found": bool(checkout),
            }
        )

    def _external_subscription_id(self, resource):
        return (
            resource.get("id")
            or resource.get("billing_agreement_id")
            or resource.get("subscription_id")
            or resource.get("supplementary_data", {})
            .get("related_ids", {})
            .get("subscription_id", "")
        )

    def _checkout_for_external_id(self, external_id):
        if not external_id:
            return None
        return (
            CheckoutSession.objects.select_related("plan", "business_client")
            .filter(external_checkout_id=external_id)
            .first()
        )

    def _activate_subscription(self, checkout):
        return activate_checkout_subscription(
            checkout,
            external_subscription_id=checkout.external_checkout_id,
        )

    def _cancel_subscription(self, checkout):
        return cancel_checkout_subscription(
            checkout,
            external_subscription_id=checkout.external_checkout_id,
        )

    def _verify_paypal_signature(self, request, event):
        if settings.DEBUG and not settings.KALEYA_PAYPAL_WEBHOOK_ID:
            return True, ""
        if not settings.KALEYA_PAYPAL_WEBHOOK_ID:
            return False, "PAYPAL_WEBHOOK_ID nije podesen u .env fajlu."
        try:
            token = self._paypal_access_token()
            payload = {
                "auth_algo": request.headers.get("PAYPAL-AUTH-ALGO", ""),
                "cert_url": request.headers.get("PAYPAL-CERT-URL", ""),
                "transmission_id": request.headers.get("PAYPAL-TRANSMISSION-ID", ""),
                "transmission_sig": request.headers.get("PAYPAL-TRANSMISSION-SIG", ""),
                "transmission_time": request.headers.get("PAYPAL-TRANSMISSION-TIME", ""),
                "webhook_id": settings.KALEYA_PAYPAL_WEBHOOK_ID,
                "webhook_event": event,
            }
            data = self._paypal_json_request(
                f"{self._paypal_api_base()}/v1/notifications/verify-webhook-signature",
                token,
                payload,
            )
        except Exception as exc:
            return False, self._paypal_error_message(exc)
        if data.get("verification_status") == "SUCCESS":
            return True, ""
        return False, "PayPal webhook potpis nije validan."

    def _paypal_api_base(self):
        if settings.KALEYA_PAYPAL_ENVIRONMENT == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    def _paypal_access_token(self):
        credentials = f"{settings.KALEYA_PAYPAL_CLIENT_ID}:{settings.KALEYA_PAYPAL_CLIENT_SECRET}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("ascii")
        form = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("ascii")
        request = urllib.request.Request(
            f"{self._paypal_api_base()}/v1/oauth2/token",
            data=form,
            headers={
                "Authorization": f"Basic {encoded}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data.get("access_token", "")

    def _paypal_json_request(self, url, token, payload):
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))

    def _paypal_error_message(self, exc):
        if isinstance(exc, urllib.error.HTTPError):
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            return f"PayPal greska {exc.code}: {body or exc.reason}"
        return f"PayPal greska: {exc}"
