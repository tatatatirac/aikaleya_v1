import secrets

from django.http import HttpResponse

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response

from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user
from integrations.models import IntegrationConnection
from integrations.serializers import IntegrationConnectionSerializer
from integrations.services import (
    configure_telegram_webhook,
    integration_rows_for_client,
    process_telegram_webhook,
    process_whatsapp_webhook,
    process_viber_webhook,
    queue_test_message,
    telegram_api_post,
)


class IntegrationConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationConnectionSerializer
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
            return IntegrationConnection.objects.none()
        return IntegrationConnection.objects.filter(business_client=client)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = self.get_client()
        return context

    def perform_create(self, serializer):
        serializer.save(business_client=self.get_client())

    @action(detail=False, methods=["get"], url_path="status")
    def connection_status(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"business_client": client.id, "integrations": integration_rows_for_client(client)})

    @action(detail=False, methods=["post"], url_path="test-message")
    def test_message(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)
        if getattr(client, "is_demo", False):
            return Response(
                {"detail": "Demo nalog ne salje stvarne test poruke niti koristi spoljne integracije."},
                status=status.HTTP_403_FORBIDDEN,
            )

        provider = request.data.get("provider", "")
        to_value = request.data.get("to", "")
        body = request.data.get("body", "")
        if not to_value:
            return Response({"to": "Unesite broj telefona, email ili ID primaoca."}, status=status.HTTP_400_BAD_REQUEST)
        if not body:
            return Response({"body": "Unesite tekst test poruke."}, status=status.HTTP_400_BAD_REQUEST)

        conversation, message = queue_test_message(client, provider, to_value, body)
        return Response(
            {
                "status": "queued",
                "delivery_note": "Poruka je upisana u red za slanje. Stvarno slanje se ukljucuje kada se poveze provider nalog.",
                "conversation_id": conversation.id,
                "message_id": message.id,
                "provider": provider,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["post"], url_path="telegram-setup")
    def telegram_setup(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)
        if getattr(client, "is_demo", False):
            return Response(
                {"detail": "Demo nalog ne koristi spoljne integracije."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bot_token = (request.data.get("bot_token") or "").strip()
        if not bot_token:
            return Response({"bot_token": "Unesi bot token."}, status=status.HTTP_400_BAD_REQUEST)

        webhook_secret = secrets.token_urlsafe(32)
        connection, _created = IntegrationConnection.objects.update_or_create(
            business_client=client,
            provider="telegram",
            defaults={
                "config": {"bot_token": bot_token, "webhook_secret": webhook_secret},
                "enabled": True,
                "status": "draft",
                "last_error": "",
            },
        )

        webhook_url = request.build_absolute_uri(
            f"/api/integrations/telegram/webhook/{connection.id}/"
        )

        try:
            configure_telegram_webhook(connection, webhook_url)
        except Exception as exc:
            connection.status = "error"
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        bot_username = ""
        try:
            bot_info = telegram_api_post(connection, "getMe", {})
            if bot_info.get("ok") and bot_info.get("result"):
                bot_username = bot_info["result"].get("username", "")
        except Exception:
            pass

        if bot_username:
            connection.public_number = f"@{bot_username}"
            connection.save(update_fields=["public_number", "updated_at"])

        return Response(
            {
                "ok": True,
                "connection_id": connection.id,
                "bot_username": bot_username,
                "webhook_url": webhook_url,
                "status": "connected",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="telegram-disconnect")
    def telegram_disconnect(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)

        connection = IntegrationConnection.objects.filter(
            business_client=client, provider="telegram"
        ).first()
        if not connection:
            return Response({"detail": "Telegram integracija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)

        try:
            telegram_api_post(connection, "deleteWebhook", {"drop_pending_updates": "false"})
        except Exception:
            pass

        connection.enabled = False
        connection.status = "draft"
        connection.webhook_url = ""
        connection.config = {}
        connection.last_error = ""
        connection.save(update_fields=["enabled", "status", "webhook_url", "config", "last_error", "updated_at"])

        return Response({"ok": True}, status=status.HTTP_200_OK)


class TelegramWebhookAPIView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request, connection_id):
        connection = (
            IntegrationConnection.objects.select_related("business_client")
            .filter(id=connection_id, provider="telegram")
            .first()
        )
        if not connection:
            return Response({"detail": "Telegram integracija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)

        provided_secret = (
            request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            or request.query_params.get("secret", "")
        )
        try:
            result = process_telegram_webhook(connection, request.data, provided_secret)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            connection.status = "error"
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if connection.status == "error":
            connection.status = "connected"
            connection.last_error = ""
            connection.save(update_fields=["status", "last_error", "updated_at"])
        return Response(result, status=status.HTTP_200_OK)


class WhatsAppWebhookAPIView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def get(self, request, connection_id):
        """Handle Meta's webhook verification challenge (hub.challenge)."""
        connection = IntegrationConnection.objects.filter(id=connection_id, provider="whatsapp").first()
        if not connection:
            return Response({"detail": "WhatsApp integracija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)

        mode = request.query_params.get("hub.mode", "")
        verify_token = request.query_params.get("hub.verify_token", "")
        challenge = request.query_params.get("hub.challenge", "")

        expected_token = (connection.config or {}).get("verify_token", "")
        if mode == "subscribe" and expected_token and verify_token == expected_token:
            return HttpResponse(challenge, content_type="text/plain", status=200)
        return Response({"detail": "Verifikacija nije uspela."}, status=status.HTTP_403_FORBIDDEN)

    def post(self, request, connection_id):
        connection = (
            IntegrationConnection.objects.select_related("business_client")
            .filter(id=connection_id, provider="whatsapp")
            .first()
        )
        if not connection:
            return Response({"detail": "WhatsApp integracija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)

        body_bytes = request.body
        signature = request.headers.get("X-Hub-Signature-256", "")
        try:
            result = process_whatsapp_webhook(connection, request.data, body_bytes, signature)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            connection.status = "error"
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if connection.status == "error":
            connection.status = "connected"
            connection.last_error = ""
            connection.save(update_fields=["status", "last_error", "updated_at"])
        return Response(result, status=status.HTTP_200_OK)


class ViberWebhookAPIView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request, connection_id):
        connection = (
            IntegrationConnection.objects.select_related("business_client")
            .filter(id=connection_id, provider="viber")
            .first()
        )
        if not connection:
            return Response({"detail": "Viber integracija nije pronadjena."}, status=status.HTTP_404_NOT_FOUND)

        body_bytes = request.body
        signature = request.headers.get("X-Viber-Content-Signature", "")
        try:
            result = process_viber_webhook(connection, request.data, body_bytes, signature)
        except PermissionDenied as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            connection.status = "error"
            connection.last_error = str(exc)
            connection.save(update_fields=["status", "last_error", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if connection.status == "error":
            connection.status = "connected"
            connection.last_error = ""
            connection.save(update_fields=["status", "last_error", "updated_at"])
        return Response(result, status=status.HTTP_200_OK)
