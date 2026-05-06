from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile
from billing.models import Plan
from clients.models import BusinessClient
from support.models import SupportTicket


class SupportTicketApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="test12345",
        )
        self.business = BusinessClient.objects.create(
            owner=self.owner,
            name="Support Test Business",
            package=Plan.CODE_BUSINESS_PLUS,
        )
        self.ticket = SupportTicket.objects.create(
            business_client=self.business,
            subject="Kaleya support handoff",
            message="Kaleya nije mogla da zavrsi zahtev.",
            priority=SupportTicket.PRIORITY_URGENT,
        )
        self.employee = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="test12345",
        )
        self.employee.profile.role = Profile.ROLE_EMPLOYEE
        self.employee.profile.business_client = self.business
        self.employee.profile.save(update_fields=["role", "business_client", "updated_at"])

    def response_rows(self, response):
        return response.data.get("results", response.data)

    def test_owner_can_list_and_update_support_ticket_status(self):
        self.api.force_authenticate(self.owner)

        list_response = self.api.get("/api/support/tickets/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(self.response_rows(list_response)[0]["id"], self.ticket.id)

        update_response = self.api.patch(
            f"/api/support/tickets/{self.ticket.id}/",
            {"status": SupportTicket.STATUS_RESOLVED},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["status"], SupportTicket.STATUS_RESOLVED)

    def test_employee_cannot_access_owner_support_inbox(self):
        self.api.force_authenticate(self.employee)

        list_response = self.api.get("/api/support/tickets/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(self.response_rows(list_response), [])

        create_response = self.api.post(
            "/api/support/tickets/",
            {"subject": "Employee ticket", "message": "Test"},
            format="json",
        )
        self.assertEqual(create_response.status_code, 403)
