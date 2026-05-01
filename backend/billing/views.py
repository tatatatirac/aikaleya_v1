import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, user_role
from billing.models import CheckoutSession, Plan, Subscription
from billing.serializers import CheckoutSessionCreateSerializer, CheckoutSessionSerializer, PlanSerializer, SubscriptionSerializer
from billing.services import entitlements_for_client, plan_for_client, subscription_state_for_client
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


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsAdminRole()]

    def get_queryset(self):
        return Plan.objects.filter(active=True)


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
        plan = Plan.objects.filter(code=payload["plan_code"], active=True).first()
        if not plan:
            return Response({"detail": "Paket nije pronadjen."}, status=status.HTTP_400_BAD_REQUEST)

        metadata = {
            "plan_code": plan.code,
            "note": payload.get("note", ""),
            "source": "kaleya_frontend",
        }
        checkout = CheckoutSession.objects.create(
            plan=plan,
            provider=CheckoutSession.PROVIDER_MANUAL,
            status=CheckoutSession.STATUS_MANUAL_CONTACT,
            email=payload.get("email", ""),
            company=payload.get("company", ""),
            full_name=payload.get("full_name", ""),
            amount=plan.monthly_price,
            currency=plan.currency,
            trial_days=plan.trial_days,
            metadata=metadata,
        )

        payment_provider_configured = self._payment_provider_is_configured(plan)
        message = "Payment provider jos nije povezan. Zahtev je sacuvan za rucni kontakt."

        if plan.is_contact_only:
            message = "Ovaj paket ide kroz direktan kontakt i dogovor."
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
        return Response(data, status=status.HTTP_201_CREATED)

    def _payment_provider_is_configured(self, plan):
        if settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_PAYPAL:
            return self._paypal_is_configured(plan)
        if settings.KALEYA_PAYMENT_PROVIDER == CheckoutSession.PROVIDER_STRIPE:
            return self._stripe_is_configured(plan)
        return False

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
        if not checkout.business_client:
            return
        Subscription.objects.update_or_create(
            business_client=checkout.business_client,
            defaults={
                "plan": checkout.plan,
                "status": Subscription.STATUS_ACTIVE,
                "external_subscription_id": checkout.external_checkout_id,
            },
        )

    def _cancel_subscription(self, checkout):
        if not checkout.business_client:
            return
        Subscription.objects.filter(business_client=checkout.business_client).update(
            status=Subscription.STATUS_CANCELLED,
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
