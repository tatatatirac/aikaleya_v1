import hashlib
import hmac
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
    if connection.status not in {"connected", "error"}:
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


# ===== WHATSAPP =====

def extract_whatsapp_message(data):
    """Extract the first message object and contact name from a WhatsApp Business API webhook payload."""
    try:
        value = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None, ""
        message = messages[0]
        contacts = value.get("contacts", [])
        contact_name = contacts[0].get("profile", {}).get("name", "") if contacts else ""
        return message, contact_name
    except (IndexError, KeyError, TypeError):
        return None, ""


def whatsapp_sender_label(message, contact_name=""):
    sender_id = message.get("from", "")
    if contact_name:
        return contact_name
    return f"+{sender_id}" if sender_id else "WhatsApp korisnik"


def verify_whatsapp_signature(connection, body_bytes, signature_header):
    """Verify X-Hub-Signature-256 using app_secret from config (optional — skipped if not set)."""
    app_secret = (connection.config or {}).get("app_secret", "")
    if not app_secret:
        return  # signature verification not configured
    provided = (signature_header or "").removeprefix("sha256=")
    if not provided:
        raise PermissionDenied("WhatsApp webhook signature nije pronadjen.")
    expected = hmac.new(app_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise PermissionDenied("WhatsApp webhook signature nije validan.")


def validate_whatsapp_connection(connection):
    if connection.provider != "whatsapp":
        raise serializers.ValidationError({"provider": "Integracija nije WhatsApp."})
    enforce_channel_allowed(connection.business_client, "whatsapp")
    if not connection.enabled:
        raise serializers.ValidationError({"integration": "WhatsApp integracija nije ukljucena."})
    if connection.status not in {"connected", "error"}:
        raise serializers.ValidationError({"integration": "WhatsApp integracija nije povezana."})
    missing = missing_config_keys("whatsapp", connection)
    if missing:
        raise serializers.ValidationError({"config": f"Nedostaje konfiguracija: {', '.join(missing)}."})


def send_whatsapp_message(connection, to_number, text):
    config = connection.config or {}
    access_token = config.get("access_token", "")
    phone_number_id = config.get("phone_number_id", "")
    if not access_token or not phone_number_id:
        raise serializers.ValidationError({"config": "WhatsApp access_token ili phone_number_id nije podesen."})
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text or ""},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://graph.facebook.com/v19.0/{phone_number_id}/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
    except Exception as exc:
        return {"error": str(exc)}


def process_whatsapp_webhook(connection, data, body_bytes=b"", signature_header=""):
    verify_whatsapp_signature(connection, body_bytes, signature_header)
    validate_whatsapp_connection(connection)

    message, contact_name = extract_whatsapp_message(data)
    if not message:
        return {"processed": False, "ignored": True, "reason": "Nema poruke u WhatsApp webhook-u."}

    msg_type = message.get("type", "")
    if msg_type != "text":
        return {"processed": False, "ignored": True, "reason": f"WhatsApp poruka tipa '{msg_type}' se ignorise."}

    text = (message.get("text") or {}).get("body", "").strip()
    if not text or not has_meaningful_text(text):
        return {"processed": False, "ignored": True, "reason": "WhatsApp poruka nema tekst."}

    sender_id = message.get("from", "")
    if not sender_id:
        raise serializers.ValidationError({"from": "WhatsApp sender ID nije pronadjen."})

    business_client = connection.business_client
    external_thread_id = f"whatsapp:{sender_id}"
    payload = {
        "customer_name": whatsapp_sender_label(message, contact_name),
        "channel": "whatsapp",
        "whatsapp_sender_id": sender_id,
        "whatsapp_message_id": message.get("id", ""),
    }

    result = handle_inbound_text(
        business_client,
        text,
        channel="whatsapp",
        payload=payload,
        use_ai=False if getattr(business_client, "is_demo", False) else True,
        include_voice=False,
        external_thread_id=external_thread_id,
        record_messages=True,
    )
    wa_response = send_whatsapp_message(connection, sender_id, result["response_text"])

    conversation = Conversation.objects.filter(
        business_client=business_client,
        channel="whatsapp",
        external_thread_id=external_thread_id,
    ).order_by("-updated_at").first()
    if conversation:
        metadata = conversation.metadata or {}
        metadata["whatsapp"] = {
            "sender_id": sender_id,
            "message_id": message.get("id", ""),
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
        "whatsapp_sent": "error" not in wa_response,
    }


# ===== VIBER =====

def verify_viber_signature(connection, body_bytes, signature_header):
    """Verify X-Viber-Content-Signature (HMAC-SHA256 with auth_token as key)."""
    auth_token = (connection.config or {}).get("auth_token", "")
    if not auth_token:
        raise PermissionDenied("Viber auth_token nije podesen.")
    provided = (signature_header or "").strip()
    if not provided:
        raise PermissionDenied("Viber webhook signature nije pronadjen.")
    expected = hmac.new(auth_token.encode(), body_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise PermissionDenied("Viber webhook signature nije validan.")


def validate_viber_connection(connection):
    if connection.provider != "viber":
        raise serializers.ValidationError({"provider": "Integracija nije Viber."})
    enforce_channel_allowed(connection.business_client, "viber")
    if not connection.enabled:
        raise serializers.ValidationError({"integration": "Viber integracija nije ukljucena."})
    if connection.status not in {"connected", "error"}:
        raise serializers.ValidationError({"integration": "Viber integracija nije povezana."})
    missing = missing_config_keys("viber", connection)
    if missing:
        raise serializers.ValidationError({"config": f"Nedostaje konfiguracija: {', '.join(missing)}."})


def viber_sender_label(data):
    sender = data.get("sender") or {}
    return sender.get("name") or sender.get("id") or "Viber korisnik"


def send_viber_message(connection, receiver_id, text):
    config = connection.config or {}
    auth_token = config.get("auth_token", "")
    sender_name = config.get("sender_name", "Kaleya")
    if not auth_token:
        raise serializers.ValidationError({"config": "Viber auth_token nije podesen."})
    payload = json.dumps({
        "receiver": receiver_id,
        "type": "text",
        "text": text or "",
        "sender": {"name": sender_name},
        "min_api_version": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://chatapi.viber.com/pa/send_message",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Viber-Auth-Token": auth_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8")
        return json.loads(body)
    except Exception as exc:
        return {"status": -1, "status_message": str(exc)}


def configure_viber_webhook(connection, webhook_url=""):
    """Register / update the Viber Public Account webhook via Viber REST API."""
    config = connection.config or {}
    auth_token = config.get("auth_token", "")
    target_url = (webhook_url or connection.webhook_url or "").strip()
    if not auth_token:
        raise serializers.ValidationError({"auth_token": "Viber auth_token nije podesen."})
    if not target_url:
        raise serializers.ValidationError({"webhook_url": "Viber webhook URL nije podesen."})

    payload = json.dumps({
        "url": target_url,
        "event_types": ["delivered", "seen", "failed", "subscribed", "unsubscribed", "conversation_started", "message"],
        "send_name": True,
        "send_photo": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://chatapi.viber.com/pa/set_webhook",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-Viber-Auth-Token": auth_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
        result = json.loads(body)
    except Exception as exc:
        raise serializers.ValidationError({"viber": f"Viber API error: {exc}"})

    status_code = result.get("status", -1)
    if status_code != 0:
        msg = result.get("status_message") or f"Viber error {status_code}"
        raise serializers.ValidationError({"viber": msg})

    connection.webhook_url = target_url
    connection.enabled = True
    connection.status = "connected"
    connection.last_error = ""
    connection.save(update_fields=["webhook_url", "enabled", "status", "last_error", "updated_at"])
    return result


def process_viber_webhook(connection, data, body_bytes=b"", signature_header=""):
    verify_viber_signature(connection, body_bytes, signature_header)

    event = data.get("event", "")
    # Viber sends "webhook" event on successful registration — acknowledge silently
    if event in {"webhook", "conversation_started", "subscribed", "unsubscribed", "delivered", "seen", "failed"}:
        return {"processed": False, "ignored": True, "reason": f"Viber event '{event}' se ignorise."}
    if event != "message":
        return {"processed": False, "ignored": True, "reason": f"Viber event '{event}' se ignorise."}

    validate_viber_connection(connection)

    msg_type = (data.get("message") or {}).get("type", "")
    if msg_type != "text":
        return {"processed": False, "ignored": True, "reason": f"Viber poruka tipa '{msg_type}' se ignorise."}

    text = ((data.get("message") or {}).get("text") or "").strip()
    if not text or not has_meaningful_text(text):
        return {"processed": False, "ignored": True, "reason": "Viber poruka nema tekst."}

    sender = data.get("sender") or {}
    sender_id = sender.get("id", "")
    if not sender_id:
        raise serializers.ValidationError({"sender": "Viber sender ID nije pronadjen."})

    business_client = connection.business_client
    external_thread_id = f"viber:{sender_id}"
    payload = {
        "customer_name": viber_sender_label(data),
        "channel": "viber",
        "viber_sender_id": sender_id,
    }

    result = handle_inbound_text(
        business_client,
        text,
        channel="viber",
        payload=payload,
        use_ai=False if getattr(business_client, "is_demo", False) else True,
        include_voice=False,
        external_thread_id=external_thread_id,
        record_messages=True,
    )
    viber_response = send_viber_message(connection, sender_id, result["response_text"])

    conversation = Conversation.objects.filter(
        business_client=business_client,
        channel="viber",
        external_thread_id=external_thread_id,
    ).order_by("-updated_at").first()
    if conversation:
        metadata = conversation.metadata or {}
        metadata["viber"] = {
            "sender_id": sender_id,
            "message_token": str(data.get("message_token", "")),
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
        "viber_sent": viber_response.get("status") == 0,
    }


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

    try:
        telegram_api_post(connection, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
    except Exception:
        pass

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
