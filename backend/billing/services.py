from dataclasses import dataclass

from rest_framework import serializers

from billing.models import Plan, Subscription
from staff_services.models import StaffMember


@dataclass(frozen=True)
class PlanLimits:
    max_staff_members: int | None
    allow_sms: bool
    allow_phone_calls: bool
    allow_instagram_dm: bool
    allow_tiktok_dm: bool
    allow_client_api_override: bool


FALLBACK_LIMITS = {
    Plan.CODE_BASIC: PlanLimits(0, False, False, False, False, False),
    Plan.CODE_PRO: PlanLimits(1, False, False, True, True, False),
    Plan.CODE_BUSINESS: PlanLimits(5, False, False, True, True, True),
    Plan.CODE_BUSINESS_PLUS: PlanLimits(15, True, True, True, True, True),
    Plan.CODE_BUSINESS_PRO_PLUS: PlanLimits(None, True, True, True, True, True),
    Plan.CODE_GOD_MODE: PlanLimits(None, True, True, True, True, True),
}


def plan_for_client(business_client):
    subscription = (
        Subscription.objects.select_related("plan")
        .filter(business_client=business_client)
        .first()
    )
    if subscription:
        return subscription.plan
    return Plan.objects.filter(code=business_client.package, active=True).first()


def limits_for_client(business_client):
    plan = plan_for_client(business_client)
    fallback = FALLBACK_LIMITS.get(business_client.package, FALLBACK_LIMITS[Plan.CODE_BASIC])
    if not plan:
        return fallback
    return PlanLimits(
        max_staff_members=plan.max_staff_members,
        allow_sms=plan.allow_sms,
        allow_phone_calls=plan.allow_phone_calls,
        allow_instagram_dm=plan.allow_instagram_dm,
        allow_tiktok_dm=plan.allow_tiktok_dm,
        allow_client_api_override=plan.allow_client_api_override,
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

