from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from billing.models import Plan, Subscription
from clients.models import BusinessClient, ClientApiSettings
from staff_services.models import StaffMember


@dataclass(frozen=True)
class PlanLimits:
    max_staff_members: int | None
    allow_whatsapp: bool
    allow_viber: bool
    allow_telegram: bool
    allow_sms: bool
    allow_phone_calls: bool
    allow_instagram_dm: bool
    allow_tiktok_dm: bool
    allow_client_api_override: bool
    allow_more_languages_by_agreement: bool
    includes_elevenlabs_voice: bool


FALLBACK_LIMITS = {
    Plan.CODE_BASIC: PlanLimits(0, True, True, True, False, False, False, False, False, False, False),
    Plan.CODE_PRO: PlanLimits(1, True, True, True, False, False, True, True, False, False, False),
    Plan.CODE_BUSINESS: PlanLimits(5, True, True, True, False, False, True, True, True, True, False),
    Plan.CODE_BUSINESS_PLUS: PlanLimits(15, True, True, True, True, True, True, True, True, True, True),
    Plan.CODE_BUSINESS_PRO_PLUS: PlanLimits(None, True, True, True, True, True, True, True, True, True, True),
    Plan.CODE_GOD_MODE: PlanLimits(None, True, True, True, True, True, True, True, True, True, True),
}

CHANNEL_FEATURE_MAP = {
    "whatsapp": "allow_whatsapp",
    "viber": "allow_viber",
    "telegram": "allow_telegram",
    "sms": "allow_sms",
    "phone": "allow_phone_calls",
    "phone_call": "allow_phone_calls",
    "instagram": "allow_instagram_dm",
    "instagram_dm": "allow_instagram_dm",
    "tiktok": "allow_tiktok_dm",
    "tiktok_dm": "allow_tiktok_dm",
}

ALWAYS_ALLOWED_CHANNELS = {"web", "email", "dashboard", "google_calendar"}


def plan_for_client(business_client):
    subscription = subscription_for_client(business_client)
    if subscription:
        return subscription.plan
    return Plan.objects.filter(code=business_client.package, active=True).first()


def subscription_for_client(business_client):
    return (
        Subscription.objects.select_related("plan")
        .filter(business_client=business_client)
        .first()
    )


def subscription_state(subscription):
    if not subscription:
        return {
            "status": "none",
            "trial_ends_at": None,
            "trial_is_active": False,
            "trial_days_left": 0,
            "is_access_active": True,
            "current_period_start": None,
            "current_period_end": None,
            "plan": None,
        }
    return {
        "status": subscription.status,
        "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
        "trial_is_active": subscription.trial_is_active,
        "trial_days_left": subscription.trial_days_left,
        "is_access_active": subscription.is_access_active,
        "current_period_start": (
            subscription.current_period_start.isoformat() if subscription.current_period_start else None
        ),
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "plan": {
            "code": subscription.plan.code,
            "name": subscription.plan.name,
        },
    }


def subscription_state_for_client(business_client):
    return subscription_state(subscription_for_client(business_client))


def limits_for_client(business_client):
    plan = plan_for_client(business_client)
    fallback = FALLBACK_LIMITS.get(business_client.package, FALLBACK_LIMITS[Plan.CODE_BASIC])
    if not plan:
        return fallback
    return PlanLimits(
        max_staff_members=plan.max_staff_members,
        allow_whatsapp=plan.allow_whatsapp,
        allow_viber=plan.allow_viber,
        allow_telegram=plan.allow_telegram,
        allow_sms=plan.allow_sms,
        allow_phone_calls=plan.allow_phone_calls,
        allow_instagram_dm=plan.allow_instagram_dm,
        allow_tiktok_dm=plan.allow_tiktok_dm,
        allow_client_api_override=plan.allow_client_api_override,
        allow_more_languages_by_agreement=plan.allow_more_languages_by_agreement,
        includes_elevenlabs_voice=plan.includes_elevenlabs_voice,
    )


def entitlements_for_client(business_client):
    limits = limits_for_client(business_client)
    return {
        "max_staff_members": limits.max_staff_members,
        "allow_whatsapp": limits.allow_whatsapp,
        "allow_viber": limits.allow_viber,
        "allow_telegram": limits.allow_telegram,
        "allow_sms": limits.allow_sms,
        "allow_phone_calls": limits.allow_phone_calls,
        "allow_instagram_dm": limits.allow_instagram_dm,
        "allow_tiktok_dm": limits.allow_tiktok_dm,
        "allow_client_api_override": limits.allow_client_api_override,
        "allow_more_languages_by_agreement": limits.allow_more_languages_by_agreement,
        "includes_elevenlabs_voice": limits.includes_elevenlabs_voice,
        "allowed_channels": sorted(
            channel
            for channel in (
                "web",
                "email",
                "whatsapp",
                "viber",
                "telegram",
                "sms",
                "phone",
                "instagram",
                "tiktok",
                "google_calendar",
            )
            if channel_allowed(limits, channel)
        ),
    }


def channel_allowed(limits, channel):
    normalized = (channel or "").strip().lower()
    if normalized in ALWAYS_ALLOWED_CHANNELS:
        return True
    feature = CHANNEL_FEATURE_MAP.get(normalized)
    if not feature:
        return False
    return bool(getattr(limits, feature))


def enforce_channel_allowed(business_client, channel):
    limits = limits_for_client(business_client)
    if channel_allowed(limits, channel):
        return
    raise serializers.ValidationError(
        {
            "package": (
                f"Kanal '{channel}' nije ukljucen u trenutni paket. "
                "Nadogradite paket da biste ukljucili ovaj kanal."
            )
        }
    )


def enforce_client_api_override_allowed(business_client):
    limits = limits_for_client(business_client)
    if limits.allow_client_api_override:
        return
    raise serializers.ValidationError(
        {
            "package": (
                "API po klijentu nije ukljucen u trenutni paket. "
                "Ova opcija pocinje od Business paketa."
            )
        }
    )


def enforce_elevenlabs_voice_allowed(business_client):
    limits = limits_for_client(business_client)
    if limits.includes_elevenlabs_voice:
        return
    raise serializers.ValidationError(
        {
            "package": (
                "ElevenLabs AI voice nije ukljucen u trenutni paket. "
                "Ova opcija pocinje od Business+ paketa."
            )
        }
    )


def active_staff_count(business_client):
    return StaffMember.objects.filter(business_client=business_client, is_active=True).count()


def enforce_staff_limit(business_client, adding=1):
    limits = limits_for_client(business_client)
    if limits.max_staff_members is None:
        return
    if active_staff_count(business_client) + adding > limits.max_staff_members:
        raise serializers.ValidationError(
            {
                "package": (
                    f"Paket dozvoljava najvise {limits.max_staff_members} aktivnih zaposlenih. "
                    "Nadogradite paket za dodatne zaposlene."
                )
            }
        )


def activate_pending_registration_for_checkout(checkout):
    if checkout.business_client:
        return checkout.business_client

    pending = getattr(checkout, "pending_registration", None)
    if not pending or not pending.email or not pending.password_hash:
        return None

    existing_user = (
        User.objects.filter(email__iexact=pending.email).first()
        or User.objects.filter(username__iexact=pending.email).first()
    )
    if existing_user:
        existing_client = BusinessClient.objects.filter(owner=existing_user).first()
        if existing_client:
            checkout.business_client = existing_client
            checkout.save(update_fields=["business_client", "updated_at"])
            return existing_client
        return None

    with transaction.atomic():
        full_name = pending.full_name.strip()
        first_name, _, last_name = full_name.partition(" ")
        user = User.objects.create(
            username=pending.email,
            email=pending.email,
            first_name=first_name,
            last_name=last_name,
            password=pending.password_hash,
        )
        user.profile.role = "client"
        user.profile.phone = pending.phone
        user.profile.save(update_fields=["role", "phone", "updated_at"])

        client = BusinessClient.objects.create(
            owner=user,
            name=pending.company,
            public_name=pending.company,
            package=checkout.plan.code,
            language="en",
            interface_language="en",
            voice_language="en",
            timezone="Europe/Belgrade",
            kaleya_enabled=True,
        )
        user.profile.business_client = client
        user.profile.save(update_fields=["business_client", "updated_at"])

        ClientApiSettings.objects.get_or_create(
            business_client=client,
            defaults={
                "ai_provider": "anthropic",
                "ai_model": "claude-haiku-4-5-20251001",
                "voice_provider": "elevenlabs",
                "voice_model": "eleven_multilingual_v2",
            },
        )

        checkout.business_client = client
        checkout.save(update_fields=["business_client", "updated_at"])
        pending.activated_at = timezone.now()
        pending.save(update_fields=["activated_at", "updated_at"])
        return client


def activate_checkout_subscription(checkout, external_customer_id="", external_subscription_id=""):
    business_client = activate_pending_registration_for_checkout(checkout)
    if not business_client:
        return None

    subscription, _created = Subscription.objects.update_or_create(
        business_client=business_client,
        defaults={
            "plan": checkout.plan,
            "status": Subscription.STATUS_ACTIVE,
            "trial_ends_at": timezone.now() + timedelta(days=checkout.plan.trial_days),
            "external_customer_id": external_customer_id,
            "external_subscription_id": external_subscription_id or checkout.external_checkout_id,
        },
    )
    business_client.package = checkout.plan.code
    business_client.save(update_fields=["package", "updated_at"])
    return subscription


def mark_checkout_subscription_past_due(checkout, external_customer_id="", external_subscription_id=""):
    business_client = checkout.business_client
    if not business_client:
        return None
    return Subscription.objects.filter(business_client=business_client).update(
        status=Subscription.STATUS_PAST_DUE,
        external_customer_id=external_customer_id,
        external_subscription_id=external_subscription_id or checkout.external_checkout_id,
    )


def cancel_checkout_subscription(checkout, external_customer_id="", external_subscription_id=""):
    business_client = checkout.business_client
    if not business_client:
        return None
    return Subscription.objects.filter(business_client=business_client).update(
        status=Subscription.STATUS_CANCELLED,
        external_customer_id=external_customer_id,
        external_subscription_id=external_subscription_id or checkout.external_checkout_id,
    )
