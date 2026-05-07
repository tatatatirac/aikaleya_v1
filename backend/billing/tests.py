from datetime import time, timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from billing.models import (
    CheckoutSession,
    PaymentWebhookEvent,
    PendingCheckoutRegistration,
    Plan,
    Subscription,
)
from billing.views import CheckoutSessionViewSet
from clients.models import BusinessClient


class PackageLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner@example.com", email="owner@example.com", password="test12345")
        self.user.profile.role = "client"
        self.user.profile.save(update_fields=["role", "updated_at"])
        self.client_profile = BusinessClient.objects.create(
            owner=self.user,
            name="Test Business",
            package=Plan.CODE_BASIC,
            work_start=time(9, 0),
            work_end=time(16, 0),
        )
        self.user.profile.business_client = self.client_profile
        self.user.profile.save(update_fields=["business_client", "updated_at"])
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def make_plan(self, code, max_staff, **extra):
        defaults = {
            "allow_whatsapp": True,
            "allow_viber": True,
            "allow_telegram": True,
            "allow_sms": False,
            "allow_phone_calls": False,
            "allow_instagram_dm": False,
            "allow_tiktok_dm": False,
            "allow_client_api_override": False,
            "allow_more_languages_by_agreement": False,
            "includes_elevenlabs_voice": False,
        }
        defaults.update(extra)
        return Plan.objects.create(
            code=code,
            name=code,
            monthly_price=1,
            currency="USD",
            max_staff_members=max_staff,
            **defaults,
        )

    def test_basic_package_blocks_employee_creation(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        response = self.api.post(
            "/api/staff-services/staff/",
            {"full_name": "Ana Employee", "role_title": "Stylist", "is_active": True},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("package", response.data)

    def test_pro_package_allows_one_employee_only(self):
        plan = self.make_plan(Plan.CODE_PRO, 1)
        self.client_profile.package = Plan.CODE_PRO
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        first = self.api.post(
            "/api/staff-services/staff/",
            {"full_name": "First Employee", "role_title": "Stylist", "is_active": True},
            format="json",
        )
        second = self.api.post(
            "/api/staff-services/staff/",
            {"full_name": "Second Employee", "role_title": "Assistant", "is_active": True},
            format="json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertIn("package", second.data)

    def test_business_package_blocks_sms_integration(self):
        plan = self.make_plan(
            Plan.CODE_BUSINESS,
            5,
            allow_instagram_dm=True,
            allow_tiktok_dm=True,
            allow_client_api_override=True,
            allow_more_languages_by_agreement=True,
        )
        self.client_profile.package = Plan.CODE_BUSINESS
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        response = self.api.post(
            "/api/integrations/connections/",
            {"provider": "sms", "enabled": True, "status": "connected"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("package", response.data)

    def test_business_plus_package_allows_sms_integration(self):
        plan = self.make_plan(
            Plan.CODE_BUSINESS_PLUS,
            15,
            allow_sms=True,
            allow_phone_calls=True,
            allow_instagram_dm=True,
            allow_tiktok_dm=True,
            allow_client_api_override=True,
            allow_more_languages_by_agreement=True,
            includes_elevenlabs_voice=True,
        )
        self.client_profile.package = Plan.CODE_BUSINESS_PLUS
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        response = self.api.post(
            "/api/integrations/connections/",
            {"provider": "sms", "enabled": True, "status": "connected"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_ai_sms_channel_is_blocked_until_business_plus(self):
        plan = self.make_plan(
            Plan.CODE_BUSINESS,
            5,
            allow_instagram_dm=True,
            allow_tiktok_dm=True,
            allow_client_api_override=True,
        )
        self.client_profile.package = Plan.CODE_BUSINESS
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        response = self.api.post(
            "/api/ai-agent/inbound-text/",
            {"text": "Check free slots today", "channel": "sms", "use_ai": False},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("package", response.data)

    def test_entitlements_endpoint_returns_package_rules(self):
        plan = self.make_plan(
            Plan.CODE_BUSINESS_PLUS,
            15,
            allow_sms=True,
            allow_phone_calls=True,
            allow_instagram_dm=True,
            allow_tiktok_dm=True,
            allow_client_api_override=True,
            allow_more_languages_by_agreement=True,
            includes_elevenlabs_voice=True,
        )
        self.client_profile.package = Plan.CODE_BUSINESS_PLUS
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(business_client=self.client_profile, plan=plan)

        response = self.api.get("/api/billing/subscriptions/entitlements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["entitlements"]["max_staff_members"], 15)
        self.assertTrue(response.data["entitlements"]["allow_sms"])
        self.assertTrue(response.data["entitlements"]["includes_elevenlabs_voice"])

    def test_entitlements_endpoint_returns_subscription_state(self):
        plan = self.make_plan(Plan.CODE_PRO, 1)
        self.client_profile.package = Plan.CODE_PRO
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(
            business_client=self.client_profile,
            plan=plan,
            status=Subscription.STATUS_TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=14),
        )

        response = self.api.get("/api/billing/subscriptions/entitlements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subscription"]["status"], Subscription.STATUS_TRIAL)
        self.assertTrue(response.data["subscription"]["trial_is_active"])
        self.assertTrue(response.data["subscription"]["is_access_active"])
        self.assertGreaterEqual(response.data["subscription"]["trial_days_left"], 13)

    def test_current_subscription_endpoint_returns_access_status(self):
        plan = self.make_plan(Plan.CODE_PRO, 1)
        self.client_profile.package = Plan.CODE_PRO
        self.client_profile.save(update_fields=["package", "updated_at"])
        Subscription.objects.create(
            business_client=self.client_profile,
            plan=plan,
            status=Subscription.STATUS_TRIAL,
            trial_ends_at=timezone.now() - timedelta(days=1),
        )

        response = self.api.get("/api/billing/subscriptions/current/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["subscription"]["status"], Subscription.STATUS_TRIAL)
        self.assertFalse(response.data["subscription"]["trial_is_active"])
        self.assertFalse(response.data["subscription"]["is_access_active"])
        self.assertEqual(response.data["subscription"]["trial_days_left"], 0)

    def test_demo_client_inbound_ai_uses_fallback_without_voice(self):
        self.client_profile.is_demo = True
        self.client_profile.package = Plan.CODE_BUSINESS_PLUS
        self.client_profile.save(update_fields=["is_demo", "package", "updated_at"])

        response = self.api.post(
            "/api/ai-agent/inbound-text/",
            {"text": "check available slots today", "channel": "web", "use_ai": True, "include_voice": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["demo_mode"])
        self.assertEqual(response.data["ai_provider"], "demo-fallback")
        self.assertIsNone(response.data["voice"])

    def test_demo_client_blocks_real_tts_and_integration_test_messages(self):
        self.client_profile.is_demo = True
        self.client_profile.package = Plan.CODE_BUSINESS_PLUS
        self.client_profile.save(update_fields=["is_demo", "package", "updated_at"])

        tts = self.api.post("/api/ai-agent/tts/", {"text": "Hello"}, format="json")
        message = self.api.post(
            "/api/integrations/connections/test-message/",
            {"provider": "whatsapp", "to": "+381600000", "body": "Test"},
            format="json",
        )

        self.assertEqual(tts.status_code, 403)
        self.assertEqual(message.status_code, 403)

    @override_settings(KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_MANUAL)
    def test_checkout_session_endpoint_creates_manual_request_without_payment_provider(self):
        self.make_plan(Plan.CODE_BASIC, 0)
        api = APIClient()

        response = api.post(
            "/api/billing/checkout-sessions/",
            {
                "plan_code": Plan.CODE_BASIC,
                "email": "new-client@example.com",
                "company": "New Company",
                "full_name": "New Owner",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], CheckoutSession.STATUS_MANUAL_CONTACT)
        self.assertFalse(response.data["payment_provider_configured"])
        self.assertTrue(response.data["local_checkout_url"].startswith("/checkout.html?session="))
        self.assertEqual(CheckoutSession.objects.count(), 1)

    @override_settings(KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_MANUAL)
    def test_checkout_session_stores_pending_registration_with_hashed_password(self):
        self.make_plan(Plan.CODE_BASIC, 0)
        api = APIClient()

        response = api.post(
            "/api/billing/checkout-sessions/",
            {
                "plan_code": Plan.CODE_BASIC,
                "email": "pending-client@example.com",
                "company": "Pending Company",
                "full_name": "Pending Owner",
                "password": "strongpass123",
                "phone": "+381600001",
                "country": "Serbia",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        pending = PendingCheckoutRegistration.objects.get(email="pending-client@example.com")
        self.assertTrue(check_password("strongpass123", pending.password_hash))
        self.assertNotEqual(pending.password_hash, "strongpass123")
        self.assertEqual(pending.phone, "+381600001")
        self.assertNotIn("strongpass123", str(response.data))
        self.assertNotIn(pending.password_hash, str(response.data))

    def test_checkout_session_contact_only_plan_stays_manual(self):
        Plan.objects.create(
            code=Plan.CODE_BUSINESS_PRO_PLUS,
            name="BusinessPro+",
            monthly_price=0,
            currency="USD",
            is_contact_only=True,
            max_staff_members=None,
        )
        api = APIClient()

        response = api.post(
            "/api/billing/checkout-sessions/",
            {
                "plan_code": Plan.CODE_BUSINESS_PRO_PLUS,
                "email": "enterprise@example.com",
                "company": "Enterprise",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], CheckoutSession.STATUS_MANUAL_CONTACT)
        self.assertIn("direktan kontakt", response.data["message"])

    def test_checkout_public_detail_returns_safe_payment_data(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)
        checkout = CheckoutSession.objects.create(
            plan=plan,
            provider=CheckoutSession.PROVIDER_PAYPAL,
            status=CheckoutSession.STATUS_PROVIDER_PENDING,
            checkout_url="https://www.sandbox.paypal.com/checkoutnow?token=I-123",
            email="private@example.com",
            company="Private Company",
            full_name="Private Owner",
            amount=plan.monthly_price,
            currency=plan.currency,
        )
        api = APIClient()

        response = api.get(f"/api/billing/checkout-sessions/public/{checkout.public_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan"]["code"], Plan.CODE_BASIC)
        self.assertTrue(response.data["payment_ready"])
        self.assertEqual(response.data["provider_checkout_url"], checkout.checkout_url)
        self.assertFalse(response.data["account_activated"])
        self.assertEqual(response.data["subscription_status"], "")
        self.assertNotIn("private@example.com", str(response.data))
        self.assertNotIn("Private Company", str(response.data))
        self.assertNotIn("Private Owner", str(response.data))

    @override_settings(
        KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_PAYPAL,
        KALEYA_PAYPAL_CLIENT_ID="client-id",
        KALEYA_PAYPAL_CLIENT_SECRET="client-secret",
        KALEYA_PAYPAL_PLAN_IDS={Plan.CODE_BASIC: "P-BASIC"},
    )
    def test_paypal_configuration_detection(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)

        self.assertTrue(CheckoutSessionViewSet()._paypal_is_configured(plan))

    @override_settings(
        KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_PAYPAL,
        KALEYA_PAYPAL_CLIENT_ID="public-client-id",
        KALEYA_PAYPAL_CLIENT_SECRET="private-client-secret",
        KALEYA_PAYPAL_WEBHOOK_ID="WH-123",
        KALEYA_PAYPAL_PLAN_IDS={Plan.CODE_BASIC: "P-BASIC", Plan.CODE_PRO: ""},
    )
    def test_paypal_public_config_endpoint_returns_safe_readiness(self):
        api = APIClient()

        response = api.get("/api/billing/paypal/public-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], CheckoutSession.PROVIDER_PAYPAL)
        self.assertEqual(response.data["client_id"], "public-client-id")
        self.assertTrue(response.data["client_id_configured"])
        self.assertTrue(response.data["webhook_configured"])
        self.assertTrue(response.data["plans_configured"][Plan.CODE_BASIC])
        self.assertFalse(response.data["plans_configured"][Plan.CODE_PRO])
        self.assertTrue(response.data["ready"])
        self.assertNotIn("private-client-secret", str(response.data))

    @override_settings(
        KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_LEMONSQUEEZY,
        KALEYA_LEMONSQUEEZY_API_KEY="private-api-key",
        KALEYA_LEMONSQUEEZY_STORE_ID="12345",
        KALEYA_LEMONSQUEEZY_VARIANT_IDS={Plan.CODE_BASIC: "67890"},
    )
    def test_lemonsqueezy_configuration_detection(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)

        self.assertTrue(CheckoutSessionViewSet()._lemonsqueezy_is_configured(plan))

    @override_settings(
        KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_LEMONSQUEEZY,
        KALEYA_LEMONSQUEEZY_API_KEY="private-api-key",
        KALEYA_LEMONSQUEEZY_STORE_ID="12345",
        KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET="private-webhook-secret",
        KALEYA_LEMONSQUEEZY_TEST_MODE=True,
        KALEYA_LEMONSQUEEZY_VARIANT_IDS={Plan.CODE_BASIC: "67890", Plan.CODE_PRO: ""},
    )
    def test_lemonsqueezy_public_config_endpoint_returns_safe_readiness(self):
        api = APIClient()

        response = api.get("/api/billing/payment/public-config/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], CheckoutSession.PROVIDER_LEMONSQUEEZY)
        self.assertEqual(response.data["environment"], "test")
        self.assertTrue(response.data["client_id_configured"])
        self.assertTrue(response.data["webhook_configured"])
        self.assertTrue(response.data["plans_configured"][Plan.CODE_BASIC])
        self.assertFalse(response.data["plans_configured"][Plan.CODE_PRO])
        self.assertTrue(response.data["ready"])
        self.assertNotIn("private-api-key", str(response.data))
        self.assertNotIn("private-webhook-secret", str(response.data))

    @override_settings(DEBUG=True, KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET="")
    def test_lemonsqueezy_webhook_logs_invalid_json(self):
        api = APIClient()

        response = api.generic(
            "POST",
            "/api/billing/lemonsqueezy/webhook/",
            data=b"{bad",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        webhook_event = PaymentWebhookEvent.objects.get()
        self.assertEqual(webhook_event.provider, CheckoutSession.PROVIDER_LEMONSQUEEZY)
        self.assertEqual(webhook_event.status, PaymentWebhookEvent.STATUS_FAILED)
        self.assertFalse(webhook_event.signature_valid)
        self.assertIn("Neispravan", webhook_event.error)

    @override_settings(DEBUG=True, KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET="")
    def test_lemonsqueezy_webhook_marks_checkout_paid_and_subscription_active_in_debug(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)
        subscription = Subscription.objects.create(
            business_client=self.client_profile,
            plan=plan,
            status=Subscription.STATUS_TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=14),
        )
        checkout = CheckoutSession.objects.create(
            business_client=self.client_profile,
            plan=plan,
            provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
            status=CheckoutSession.STATUS_PROVIDER_PENDING,
            external_checkout_id="checkout_123",
            email="owner@example.com",
            amount=plan.monthly_price,
            currency=plan.currency,
        )
        api = APIClient()

        response = api.post(
            "/api/billing/lemonsqueezy/webhook/",
            {
                "meta": {
                    "event_name": "subscription_created",
                    "custom_data": {"checkout_public_id": str(checkout.public_id)},
                },
                "data": {
                    "id": "subscription_123",
                    "attributes": {"customer_id": "customer_123"},
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["webhook_event_status"], PaymentWebhookEvent.STATUS_PROCESSED)
        checkout.refresh_from_db()
        subscription.refresh_from_db()
        self.assertEqual(checkout.status, CheckoutSession.STATUS_PAID)
        self.assertEqual(checkout.external_checkout_id, "subscription_123")
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(subscription.external_subscription_id, "subscription_123")
        webhook_event = PaymentWebhookEvent.objects.get()
        self.assertEqual(webhook_event.checkout, checkout)
        self.assertEqual(webhook_event.event_name, "subscription_created")
        self.assertEqual(webhook_event.external_object_id, "subscription_123")
        self.assertEqual(webhook_event.status, PaymentWebhookEvent.STATUS_PROCESSED)
        self.assertTrue(webhook_event.signature_valid)
        self.assertIsNotNone(webhook_event.processed_at)

    @override_settings(DEBUG=True, KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET="")
    def test_lemonsqueezy_webhook_activates_pending_registration(self):
        plan = self.make_plan(Plan.CODE_PRO, 1)
        checkout = CheckoutSession.objects.create(
            plan=plan,
            provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
            status=CheckoutSession.STATUS_PROVIDER_PENDING,
            external_checkout_id="checkout_pending",
            email="paid-client@example.com",
            company="Paid Company",
            full_name="Paid Owner",
            amount=plan.monthly_price,
            currency=plan.currency,
        )
        PendingCheckoutRegistration.objects.create(
            checkout=checkout,
            email="paid-client@example.com",
            company="Paid Company",
            full_name="Paid Owner",
            password_hash=make_password("paidpass123"),
            phone="+381600002",
            country="Serbia",
        )
        api = APIClient()
        provider_trial_end = timezone.now() + timedelta(days=14)
        provider_period_end = timezone.now() + timedelta(days=44)

        response = api.post(
            "/api/billing/lemonsqueezy/webhook/",
            {
                "meta": {
                    "event_name": "subscription_created",
                    "custom_data": {"checkout_public_id": str(checkout.public_id)},
                },
                "data": {
                    "id": "subscription_pending",
                    "attributes": {
                        "customer_id": "customer_pending",
                        "trial_ends_at": provider_trial_end.isoformat(),
                        "renews_at": provider_period_end.isoformat(),
                    },
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["webhook_event_status"], PaymentWebhookEvent.STATUS_PROCESSED)
        checkout.refresh_from_db()
        self.assertIsNotNone(checkout.business_client)
        self.assertEqual(checkout.business_client.package, Plan.CODE_PRO)
        self.assertTrue(User.objects.filter(email="paid-client@example.com").exists())
        subscription = Subscription.objects.get(business_client=checkout.business_client)
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(subscription.external_customer_id, "customer_pending")
        self.assertEqual(subscription.external_subscription_id, "subscription_pending")
        self.assertEqual(subscription.trial_ends_at.date(), provider_trial_end.date())
        self.assertEqual(subscription.current_period_end.date(), provider_period_end.date())
        webhook_event = PaymentWebhookEvent.objects.get()
        self.assertEqual(webhook_event.checkout, checkout)
        self.assertEqual(webhook_event.status, PaymentWebhookEvent.STATUS_PROCESSED)
        self.assertTrue(webhook_event.signature_valid)

        public_response = api.get(f"/api/billing/checkout-sessions/public/{checkout.public_id}/")
        self.assertEqual(public_response.status_code, 200)
        self.assertTrue(public_response.data["account_activated"])
        self.assertEqual(public_response.data["subscription_status"], Subscription.STATUS_ACTIVE)
        self.assertEqual(public_response.data["login_url"], "/")

    @override_settings(DEBUG=True, KALEYA_PAYPAL_WEBHOOK_ID="")
    def test_paypal_webhook_marks_checkout_paid_and_subscription_active_in_debug(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)
        subscription = Subscription.objects.create(
            business_client=self.client_profile,
            plan=plan,
            status=Subscription.STATUS_TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=14),
        )
        CheckoutSession.objects.create(
            business_client=self.client_profile,
            plan=plan,
            provider=CheckoutSession.PROVIDER_PAYPAL,
            status=CheckoutSession.STATUS_PROVIDER_PENDING,
            external_checkout_id="I-PAYPAL123",
            email="owner@example.com",
            amount=plan.monthly_price,
            currency=plan.currency,
        )
        api = APIClient()

        response = api.post(
            "/api/billing/paypal/webhook/",
            {
                "event_type": "BILLING.SUBSCRIPTION.ACTIVATED",
                "resource": {"id": "I-PAYPAL123"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        self.assertEqual(subscription.external_subscription_id, "I-PAYPAL123")
