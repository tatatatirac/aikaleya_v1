from django.utils import timezone
from rest_framework import serializers

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
        "required_config": ("bot_token",),
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
