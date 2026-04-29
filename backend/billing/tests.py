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

    def make_plan(self, code, max_staff):
        return Plan.objects.create(
            code=code,
            name=code,
            monthly_price=1,
            currency="USD",
            max_staff_members=max_staff,
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
