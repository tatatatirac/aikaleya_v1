from datetime import time
from io import StringIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
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

    def test_telegram_status_requires_bot_token_and_webhook_secret(self):
        IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="connected",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token"},
        )

        response = self.api.get("/api/integrations/connections/status/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        telegram = next(row for row in response.data["integrations"] if row["provider"] == "telegram")
        self.assertFalse(telegram["ready"])
        self.assertIn("webhook_secret", telegram["missing_config_keys"])
        self.assertIn("bot_token", telegram["configured_keys"])
        self.assertNotIn("secret-token", str(response.data))

    def test_telegram_webhook_rejects_invalid_secret_without_changing_status(self):
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="connected",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token", "webhook_secret": "correct-secret"},
        )

        response = self.api.post(
            f"/api/integrations/telegram/webhook/{connection.id}/",
            {"update_id": 1001, "message": {"chat": {"id": 12345}, "text": "Check free slots today"}},
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        connection.refresh_from_db()
        self.assertEqual(connection.status, "connected")
        self.assertEqual(Conversation.objects.count(), 0)

    @mock.patch("integrations.services.send_telegram_message", return_value={"ok": True})
    def test_telegram_webhook_processes_text_and_sends_reply(self, send_mock):
        self.business_client.is_demo = True
        self.business_client.save(update_fields=["is_demo", "updated_at"])
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="connected",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token", "webhook_secret": "correct-secret"},
        )

        response = self.api.post(
            f"/api/integrations/telegram/webhook/{connection.id}/",
            {
                "update_id": 1002,
                "message": {
                    "message_id": 11,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {
                        "id": 222,
                        "first_name": "Liam",
                        "last_name": "Stone",
                        "username": "liamstone",
                    },
                    "text": "Check free slots today",
                },
            },
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["processed"])
        self.assertEqual(response.data["intent"], "check_availability")
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertEqual(conversation.channel, "telegram")
        self.assertEqual(conversation.external_thread_id, "telegram:12345")
        self.assertEqual(conversation.metadata["telegram"]["username"], "liamstone")
        self.assertEqual(Message.objects.count(), 2)
        send_mock.assert_called_once()
        self.assertEqual(send_mock.call_args.args[1], 12345)

    @mock.patch("integrations.services.send_telegram_message", return_value={"ok": True})
    @mock.patch("ai_agent.services.generate_anthropic_reply")
    @mock.patch("ai_agent.services.generate_anthropic_plan")
    def test_telegram_webhook_greeting_replies_without_ai(self, plan_mock, reply_mock, send_mock):
        self.business_client.interface_language = "sr"
        self.business_client.language = "sr"
        self.business_client.save(update_fields=["interface_language", "language", "updated_at"])
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="connected",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token", "webhook_secret": "correct-secret"},
        )

        response = self.api.post(
            f"/api/integrations/telegram/webhook/{connection.id}/",
            {
                "update_id": 1004,
                "message": {
                    "message_id": 13,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 222, "first_name": "Liam"},
                    "text": "dobar dan",
                },
            },
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["processed"])
        self.assertEqual(response.data["intent"], "business_info")
        self.assertEqual(response.data["tool_status"], "greeting")
        send_mock.assert_called_once()
        self.assertIn("izvolite", send_mock.call_args.args[2].lower())
        plan_mock.assert_not_called()
        reply_mock.assert_not_called()

    @mock.patch("integrations.services.send_telegram_message", return_value={"ok": True})
    def test_telegram_webhook_recovers_from_error_status(self, send_mock):
        self.business_client.interface_language = "sr"
        self.business_client.language = "sr"
        self.business_client.save(update_fields=["interface_language", "language", "updated_at"])
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="error",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token", "webhook_secret": "correct-secret"},
            last_error="Prethodna prolazna greska.",
        )

        response = self.api.post(
            f"/api/integrations/telegram/webhook/{connection.id}/",
            {
                "update_id": 1005,
                "message": {
                    "message_id": 14,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 222, "first_name": "Liam"},
                    "text": "zdravo",
                },
            },
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["processed"])
        connection.refresh_from_db()
        self.assertEqual(connection.status, "connected")
        self.assertEqual(connection.last_error, "")
        send_mock.assert_called_once()

    @mock.patch("integrations.services.send_telegram_message", return_value={"ok": True})
    def test_telegram_webhook_ignores_emoji_only_message(self, send_mock):
        self.business_client.is_demo = True
        self.business_client.save(update_fields=["is_demo", "updated_at"])
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=True,
            status="connected",
            public_number="@kaleya_test_bot",
            config={"bot_token": "secret-token", "webhook_secret": "correct-secret"},
        )

        response = self.api.post(
            f"/api/integrations/telegram/webhook/{connection.id}/",
            {
                "update_id": 1003,
                "message": {
                    "message_id": 12,
                    "chat": {"id": 12345, "type": "private"},
                    "from": {"id": 222, "first_name": "Liam"},
                    "text": "🙋‍♂️",
                },
            },
            format="json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="correct-secret",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["processed"])
        self.assertTrue(response.data["ignored"])
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        send_mock.assert_not_called()

    def test_dashboard_can_save_telegram_configuration_without_exposing_token(self):
        django_client = Client()
        django_client.force_login(self.user)

        response = django_client.post(
            "/admin/",
            {
                "section": "telegram_integration",
                "client_id": self.business_client.id,
                "telegram_enabled": "on",
                "telegram_status": "connected",
                "telegram_public_number": "@kaleya_test_bot",
                "telegram_bot_token": "123456:telegram-secret-token",
                "telegram_webhook_secret": "webhook-secret",
                "telegram_webhook_url": "https://staging.aikaleya.com/api/integrations/telegram/webhook/1/",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("#integrations", response["Location"])
        connection = IntegrationConnection.objects.get(business_client=self.business_client, provider="telegram")
        self.assertTrue(connection.enabled)
        self.assertEqual(connection.status, "connected")
        self.assertEqual(connection.public_number, "@kaleya_test_bot")
        self.assertEqual(connection.config["bot_token"], "123456:telegram-secret-token")
        self.assertEqual(connection.config["webhook_secret"], "webhook-secret")

        second_response = django_client.post(
            "/admin/",
            {
                "section": "telegram_integration",
                "client_id": self.business_client.id,
                "telegram_enabled": "on",
                "telegram_status": "paused",
                "telegram_public_number": "@kaleya_updated_bot",
                "telegram_webhook_secret": "webhook-secret-2",
                "telegram_webhook_url": "https://staging.aikaleya.com/api/integrations/telegram/webhook/1/",
            },
        )

        self.assertEqual(second_response.status_code, status.HTTP_302_FOUND)
        connection.refresh_from_db()
        self.assertEqual(connection.status, "paused")
        self.assertEqual(connection.public_number, "@kaleya_updated_bot")
        self.assertEqual(connection.config["bot_token"], "123456:telegram-secret-token")
        self.assertEqual(connection.config["webhook_secret"], "webhook-secret-2")

        page = django_client.get(f"/admin/?client_id={self.business_client.id}#integrations")
        self.assertEqual(page.status_code, status.HTTP_200_OK)
        self.assertContains(page, "Telegram bot")
        self.assertContains(page, "Bot token je sacuvan")
        self.assertNotContains(page, "123456:telegram-secret-token")

    @mock.patch("integrations.services.telegram_api_post", return_value={"ok": True, "description": "Webhook was set"})
    def test_configure_telegram_webhook_command_sets_webhook_without_printing_token(self, post_mock):
        connection = IntegrationConnection.objects.create(
            business_client=self.business_client,
            provider="telegram",
            enabled=False,
            status="draft",
            public_number="@kaleya_test_bot",
            config={"bot_token": "123456:telegram-secret-token", "webhook_secret": "webhook-secret"},
        )
        output = StringIO()

        call_command(
            "configure_telegram_webhook",
            "--connection-id",
            str(connection.id),
            "--url",
            "https://staging.aikaleya.com/api/integrations/telegram/webhook/1/",
            stdout=output,
        )

        connection.refresh_from_db()
        self.assertTrue(connection.enabled)
        self.assertEqual(connection.status, "connected")
        self.assertEqual(connection.webhook_url, "https://staging.aikaleya.com/api/integrations/telegram/webhook/1/")
        post_mock.assert_called_once()
        self.assertEqual(post_mock.call_args.args[1], "setWebhook")
        self.assertEqual(post_mock.call_args.args[2]["secret_token"], "webhook-secret")
        self.assertNotIn("123456:telegram-secret-token", output.getvalue())
        self.assertIn("Telegram webhook je konfigurisan.", output.getvalue())
