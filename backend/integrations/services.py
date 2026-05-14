import json
import re
import urllib.parse
import urllib.request

from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from ai_agent.services import handle_inbound_text
from billing.services import channel_allowed, enforce_channel_allowed, limits_for_client
from communications.models import Conversation, Message
from integrations.models import IntegrationConnection


CHANNEL_DEFINITIONS = {
    "whatsapp": {
        "label": "WhatsApp",
        "required_config": ("access_token", "phone_number_id", "verify_token"),
    },
    "viber": {
        "label": "Viber",
        "required_config": ("auth_token", "sender_name"),
    },
    "telegram": {
        "label": "Telegram",
        "required_config": ("bot_token", "webhook_secret"),
    },
    "sms": {
        "label": "SMS",
        "required_config": ("provider", "api_key", "from_number"),
    },
    "phone": {
        "label": "Phone calls",
        "required_config": ("provider", "api_key", "from_number"),
    },
    "email": {
        "label": "Email",
        "required_config": ("smtp_host", "smtp_username", "smtp_password", "from_email"),
    },
    "google_calendar": {
        "label": "Google Calendar",
        "required_config": ("client_id", "client_secret", "refresh_token"),
    },
    "instagram": {
        "label": "Instagram DM",
        "required_config": ("access_token", "business_account_id"),
    },
    "tiktok": {
        "label": "TikTok DM",
        "required_config": ("access_token", "business_account_id"),
    },
}


def configured_keys(connection):
    if not connection:
        return []
    return sorted(key for key, value in (connection.config or {}).items() if value)


def missing_config_keys(provider, connection):
    required = CHANNEL_DEFINITIONS.get(provider, {}).get("required_config", ())
    config = connection.config if connection else {}
    return [key for key in required if not config.get(key)]


def integration_rows_for_client(business_client):
    limits = limits_for_client(business_client)
    connections = {
        connection.provider: connection
        for connection in IntegrationConnection.objects.filter(business_client=business_client)
    }
    rows = []
    for provider, definition in CHANNEL_DEFINITIONS.items():
        connection = connections.get(provider)
        allowed = channel_allowed(limits, provider)
        missing = missing_config_keys(provider, connection)
        rows.append(
            {
                "provider": provider,
                "label": definition["label"],
                "allowed_by_package": allowed,
                "enabled": bool(connection.enabled) if connection else False,
                "status": connection.status if connection else "not_configured",
                "public_number": connection.public_number if connection else "",
                "webhook_url": connection.webhook_url if connection else "",
                "configured_keys": configured_keys(connection),
                "missing_config_keys": missing,
                "ready": bool(allowed and connection and connection.enabled and connection.status == "connected" and not missing),
                "last_error": connection.last_error if connection else "",
            }
        )
    return rows


def get_ready_connection(business_client, provider):
    provider = (provider or "").strip().lower()
    if provider not in CHANNEL_DEFINITIONS:
        raise serializers.ValidationError({"provider": "Nepoznat kanal integracije."})

    enforce_channel_allowed(business_client, provider)

    connection = IntegrationConnection.objects.filter(business_client=business_client, provider=provider).first()
    if not connection:
        raise serializers.ValidationError({"integration": "Kanal jos nije dodat za ovog klijenta."})
    if not connection.enabled:
        raise serializers.ValidationError({"integration": "Kanal postoji, ali nije ukljucen."})
    if connection.status != "connected":
        raise serializers.ValidationError({"integration": "Kanal nije povezan."})

    missing = missing_config_keys(provider, connection)
    if missing:
        raise serializers.ValidationError({"config": f"Nedostaje konfiguracija: {', '.join(missing)}."})
    return connection


def queue_test_message(business_client, provider, to_value, body):
    connection = get_ready_connection(business_client, provider)
    conversation = Conversation.objects.create(
        business_client=business_client,
        channel=provider,
        status="waiting",
        language=business_client.language,
        last_message_at=timezone.now(),
        metadata={
            "test_mode": True,
            "provider": provider,
            "to": to_value,
            "integration_connection_id": connection.id,
        },
    )
    message = Message.objects.create(
        conversation=conversation,
        direction="outbound",
        message_type="text",
        sender_label="Kaleya",
        body=body,
        raw_payload={
            "test_mode": True,
            "provider": provider,
            "to": to_value,
            "queued_at": timezone.now().isoformat(),
        },
    )
    return conversation, message


def telegram_message_from_update(update):
    if not isinstance(update, dict):
        return None
    return (
        update.get("message")
        or update.get("edited_message")
        or (update.get("callback_query") or {}).get("message")
    )


def telegram_text_from_message(message):
    if not isinstance(message, dict):
        return ""
    return (message.get("text") or message.get("caption") or "").strip()


def has_meaningful_text(text):
    return bool(re.search(r"[^\W_]", text or "", flags=re.UNICODE))


def telegram_sender_label(message):
    sender = message.get("from") or {}
    first_name = (sender.get("first_name") or "").strip()
    last_name = (sender.get("last_name") or "").strip()
    username = (sender.get("username") or "").strip()
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    if username and full_name:
        return f"{full_name} (@{username})"
    return full_name or (f"@{username}" if username else "Telegram korisnik")


def verify_telegram_webhook_secret(connection, provided_secret):
    expected_secret = (connection.config or {}).get("webhook_secret", "")
    if not expected_secret:
        raise PermissionDenied("Telegram webhook secret nije podesen.")
    if provided_secret != expected_secret:
        raise PermissionDenied("Telegram webhook secret nije validan.")


def validate_telegram_connection(connection):
    if connection.provider != "telegram":
        raise serializers.ValidationError({"provider": "Integracija nije Telegram."})
    enforce_channel_allowed(connection.business_client, "telegram")
    if not connection.enabled:
        raise serializers.ValidationError({"integration": "Telegram integracija nije ukljucena."})
    if connection.status != "connected":
        raise serializers.ValidationError({"integration": "Telegram integracija nije povezana."})
    missing = missing_config_keys("telegram", connection)
    if missing:
        raise serializers.ValidationError({"config": f"Nedostaje konfiguracija: {', '.join(missing)}."})


def send_telegram_message(connection, chat_id, text):
    return telegram_api_post(
        connection,
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text or "",
            "disable_web_page_preview": "true",
        },
    )


def telegram_api_post(connection, method, data):
    bot_token = (connection.config or {}).get("bot_token", "")
    if not bot_token:
        raise serializers.ValidationError({"bot_token": "Telegram bot token nije podesen."})
    payload = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/{method}",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "raw": body}


def configure_telegram_webhook(connection, webhook_url="", drop_pending_updates=False):
    if connection.provider != "telegram":
        raise serializers.ValidationError({"provider": "Integracija nije Telegram."})

    config = connection.config or {}
    bot_token = config.get("bot_token", "")
    webhook_secret = config.get("webhook_secret", "")
    target_url = (webhook_url or connection.webhook_url or "").strip()
    if not bot_token:
        raise serializers.ValidationError({"bot_token": "Telegram bot token nije podesen."})
    if not webhook_secret:
        raise serializers.ValidationError({"webhook_secret": "Telegram webhook secret nije podesen."})
    if not target_url:
        raise serializers.ValidationError({"webhook_url": "Telegram webhook URL nije podesen."})

    response = telegram_api_post(
        connection,
        "setWebhook",
        {
            "url": target_url,
            "secret_token": webhook_secret,
            "drop_pending_updates": "true" if drop_pending_updates else "false",
        },
    )
    if not response.get("ok"):
        description = response.get("description") or response.get("raw") or "Telegram nije prihvatio webhook."
        raise serializers.ValidationError({"telegram": description})

    connection.webhook_url = target_url
    connection.enabled = True
    connection.status = "connected"
    connection.last_error = ""
    connection.save(update_fields=["webhook_url", "enabled", "status", "last_error", "updated_at"])
    return response


def process_telegram_webhook(connection, update, provided_secret):
    verify_telegram_webhook_secret(connection, provided_secret)
    validate_telegram_connection(connection)

    message = telegram_message_from_update(update)
    text = telegram_text_from_message(message)
    if not message or not text:
        return {
            "processed": False,
            "ignored": True,
            "reason": "Telegram update nema tekstualnu poruku.",
        }
    if not has_meaningful_text(text):
        return {
            "processed": False,
            "ignored": True,
            "reason": "Telegram poruka sadrzi samo emoji ili simbole.",
        }

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        raise serializers.ValidationError({"chat_id": "Telegram chat id nije pronadjen."})

    sender = message.get("from") or {}
    business_client = connection.business_client
    external_thread_id = f"telegram:{chat_id}"
    payload = {
        "customer_name": telegram_sender_label(message),
        "channel": "telegram",
        "telegram_chat_id": str(chat_id),
    }
    if sender.get("id"):
        payload["telegram_user_id"] = str(sender["id"])
    if sender.get("username"):
        payload["telegram_username"] = sender["username"]

    result = handle_inbound_text(
        business_client,
        text,
        channel="telegram",
        payload=payload,
        use_ai=False if getattr(business_client, "is_demo", False) else True,
        include_voice=False,
        external_thread_id=external_thread_id,
        record_messages=True,
    )
    telegram_response = send_telegram_message(connection, chat_id, result["response_text"])
    conversation = Conversation.objects.filter(
        business_client=business_client,
        channel="telegram",
        external_thread_id=external_thread_id,
    ).order_by("-updated_at").first()
    if conversation:
        metadata = conversation.metadata or {}
        metadata["telegram"] = {
            "chat_id": str(chat_id),
            "last_update_id": update.get("update_id"),
            "sender_id": str(sender.get("id") or ""),
            "username": sender.get("username", ""),
            "connection_id": connection.id,
        }
        conversation.metadata = metadata
        conversation.save(update_fields=["metadata", "updated_at"])

    return {
        "processed": True,
        "ignored": False,
        "conversation_id": result.get("conversation_id"),
        "intent": result.get("intent"),
        "tool_status": (result.get("tool_output") or {}).get("status", ""),
        "telegram_sent": bool(telegram_response.get("ok", True)),
    }
