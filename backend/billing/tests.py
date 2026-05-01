from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from billing.models import Plan, Subscription
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
