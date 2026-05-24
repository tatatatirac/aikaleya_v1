from django.core.management.base import BaseCommand

from billing.models import Plan


PLAN_CATALOG = [
    {
        "code": Plan.CODE_BASIC,
        "name": "Starter",
        "monthly_price": 59,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 1,
        "max_staff_members": 1,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": False,
        "allow_tiktok_dm": False,
        "allow_client_api_override": False,
        "allow_more_languages_by_agreement": False,
        "includes_elevenlabs_voice": False,
        "description": "Solo or owner-only. 1 staff member. Voice + SMS included.",
        "features": [
            "AI receptionist (Kaleya)",
            "1 staff member",
            "WhatsApp + Telegram",
            "Voice calls + SMS",
            "Google Calendar sync",
            "Booking alerts & reminders",
        ],
    },
    {
        "code": Plan.CODE_PRO,
        "name": "Pro",
        "monthly_price": 89,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 2,
        "max_staff_members": 5,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": False,
        "allow_more_languages_by_agreement": False,
        "includes_elevenlabs_voice": False,
        "description": "Up to 5 staff members with individual Kaleya app access.",
        "features": [
            "Everything in Starter",
            "Up to 5 staff members",
            "Staff app access per member",
            "Schedule blocks (hourly / daily / multi-day)",
            "Instagram DM + TikTok DM",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS,
        "name": "Team 10",
        "monthly_price": 0,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 3,
        "is_contact_only": True,
        "max_staff_members": 10,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": False,
        "description": "Up to 10 staff members. Contact for pricing.",
        "features": [
            "Everything in Pro",
            "Up to 10 staff members",
            "More languages by agreement",
            "Custom API per client",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS_PLUS,
        "name": "Team 20",
        "monthly_price": 0,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 4,
        "is_contact_only": True,
        "max_staff_members": 20,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "Up to 20 staff members. Contact for pricing.",
        "features": [
            "Everything in Team 10",
            "Up to 20 staff members",
            "ElevenLabs AI voice",
            "Phone calls + SMS",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS_PRO_PLUS,
        "name": "Enterprise",
        "monthly_price": 0,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 5,
        "is_contact_only": True,
        "max_staff_members": None,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "20+ staff, custom integrations and architecture.",
        "features": [
            "Everything in Team 20",
            "20+ staff members",
            "Custom integrations",
            "Advanced architecture by agreement",
        ],
    },
    {
        "code": Plan.CODE_GOD_MODE,
        "name": "GOD MODE",
        "monthly_price": 0,
        "currency": "USD",
        "trial_days": 0,
        "sort_order": 6,
        "is_contact_only": True,
        "max_staff_members": None,
        "allow_whatsapp": True,
        "allow_viber": False,
        "allow_telegram": True,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "Full project purchase with hosting and domain.",
        "features": ["Frontend", "Backend", "AI integrations", "Deploy setup"],
    },
]


class Command(BaseCommand):
    help = "Creates or updates the Kaleya production pricing plan catalog."

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for plan_data in PLAN_CATALOG:
            _plan, was_created = Plan.objects.update_or_create(
                code=plan_data["code"],
                defaults=plan_data,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Kaleya plans ready. Created: {created}. Updated: {updated}."
            )
        )
