from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile
from clients.models import BusinessClient, BusinessKnowledgeEntry


class BusinessKnowledgeEntryApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="test12345",
        )
        self.business = BusinessClient.objects.create(
            owner=self.owner,
            name="Knowledge Test Business",
            interface_language="en",
            language="en",
        )
        self.employee = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="emp12345",
        )
        self.employee.profile.role = Profile.ROLE_EMPLOYEE
        self.employee.profile.business_client = self.business
        self.employee.profile.save(update_fields=["role", "business_client", "updated_at"])

    def test_owner_can_create_update_and_delete_knowledge_entry(self):
        self.api.force_authenticate(user=self.owner)

        create_response = self.api.post(
            "/api/clients/knowledge/",
            {
                "category": BusinessKnowledgeEntry.CATEGORY_PRICING,
                "language": "en",
                "title": "Haircut price",
                "keywords": "price,haircut",
                "answer": "A haircut costs 25 EUR.",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        entry_id = create_response.data["id"]
        self.assertEqual(BusinessKnowledgeEntry.objects.count(), 1)

        update_response = self.api.patch(
            f"/api/clients/knowledge/{entry_id}/",
            {"answer": "A haircut costs 30 EUR."},
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["answer"], "A haircut costs 30 EUR.")

        delete_response = self.api.delete(f"/api/clients/knowledge/{entry_id}/")

        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(BusinessKnowledgeEntry.objects.count(), 0)

    def test_employee_can_read_but_cannot_change_knowledge_entry(self):
        BusinessKnowledgeEntry.objects.create(
            business_client=self.business,
            category=BusinessKnowledgeEntry.CATEGORY_POLICY,
            language="en",
            title="Cancellation",
            answer="Please cancel at least 24 hours before the appointment.",
        )
        self.api.force_authenticate(user=self.employee)

        list_response = self.api.get("/api/clients/knowledge/")
        create_response = self.api.post(
            "/api/clients/knowledge/",
            {
                "category": BusinessKnowledgeEntry.CATEGORY_FAQ,
                "language": "en",
                "title": "Employee edit",
                "answer": "This should not be saved.",
            },
            format="json",
        )

        self.assertEqual(list_response.status_code, 200)
        list_rows = list_response.data.get("results", list_response.data)
        self.assertEqual(len(list_rows), 1)
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(BusinessKnowledgeEntry.objects.count(), 1)
