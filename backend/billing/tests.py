from datetime import time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from billing.models import CheckoutSession, Plan, Subscription
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
        self.assertEqual(CheckoutSession.objects.count(), 1)

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

    @override_settings(
        KALEYA_PAYMENT_PROVIDER=CheckoutSession.PROVIDER_PAYPAL,
        KALEYA_PAYPAL_CLIENT_ID="client-id",
        KALEYA_PAYPAL_CLIENT_SECRET="client-secret",
        KALEYA_PAYPAL_PLAN_IDS={Plan.CODE_BASIC: "P-BASIC"},
    )
    def test_paypal_configuration_detection(self):
        plan = self.make_plan(Plan.CODE_BASIC, 0)

        self.assertTrue(CheckoutSessionViewSet()._paypal_is_configured(plan))

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
