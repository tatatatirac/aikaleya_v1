from datetime import time

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from clients.models import BusinessClient
from communications.models import Conversation, Message
from integrations.models import IntegrationConnection


class IntegrationStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="test12345",
        )
        self.user.profile.role = "client"
        self.user.profile.save(update_fields=["role", "updated_at"])
        self.business_client = BusinessClient.objects.create(
            owner=self.user,
            name="Kaleya Integrations Test",
            package=BusinessClient.PACKAGE_BUSINESS_PLUS,
            work_start=time(9, 0),
            work_end=time(16, 0),
        )
        self.user.profile.business_client = self.business_client
        self.user.profile.save(update_fields=["business_client", "updated_at"])
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_status_endpoint_returns_safe_integration_state(self):
        IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="whatsapp",
            enabled=True,
            status="connected",
            public_number="+15550100",
            config={
                "access_token": "secret-token",
                "phone_number_id": "phone-id",
                "verify_token": "verify-token",
            },
        )

        response = self.api.get("/api/integrations/connections/status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        whatsapp = next(row for row in response.data["integrations"] if row["provider"] == "whatsapp")
        self.assertTrue(whatsapp["allowed_by_package"])
        self.assertTrue(whatsapp["ready"])
        self.assertIn("access_token", whatsapp["configured_keys"])
        self.assertNotIn("secret-token", str(response.data))

    def test_test_message_is_blocked_when_package_does_not_allow_channel(self):
        self.business_client.package = BusinessClient.PACKAGE_BASIC
        self.business_client.save(update_fields=["package", "updated_at"])

        response = self.api.post(
            "/api/integrations/connections/test-message/",
            {"provider": "sms", "to": "+15550100", "body": "Kaleya test"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("package", response.data)

    def test_connected_provider_can_queue_test_message(self):
        IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="whatsapp",
            enabled=True,
            status="connected",
            public_number="+15550100",
            config={
                "access_token": "secret-token",
                "phone_number_id": "phone-id",
                "verify_token": "verify-token",
            },
        )

        response = self.api.post(
            "/api/integrations/connections/test-message/",
            {"provider": "whatsapp", "to": "+15550101", "body": "Kaleya test"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "queued")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.first().body, "Kaleya test")
