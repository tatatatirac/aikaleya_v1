from django.core.management.base import BaseCommand

from billing.models import Plan


PLAN_CATALOG = [
    {
        "code": Plan.CODE_BASIC,
        "name": "Basic",
        "monthly_price": 59,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 1,
        "max_staff_members": 0,
        "allow_sms": False,
        "allow_phone_calls": False,
        "allow_instagram_dm": False,
        "allow_tiktok_dm": False,
        "allow_client_api_override": False,
        "allow_more_languages_by_agreement": False,
        "includes_elevenlabs_voice": False,
        "description": "Za vlasnika ili firmu bez dodatnih radnika.",
        "features": [
            "AI Kaleya zakazivanja",
            "Vlasnik/firma Kaleya APP",
            "Vlasnik zakazivanja",
            "WA + Viber + Telegram",
            "AI voice",
            "Alarmi i obavestenja",
        ],
    },
    {
        "code": Plan.CODE_PRO,
        "name": "Pro",
        "monthly_price": 119,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 2,
        "max_staff_members": 1,
        "allow_sms": False,
        "allow_phone_calls": False,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": False,
        "allow_more_languages_by_agreement": False,
        "includes_elevenlabs_voice": False,
        "description": "Za vlasnika plus jednog radnika sa Kaleya app pristupom.",
        "features": [
            "Sve iz Basic",
            "1 radnik",
            "Radnik zakazivanja",
            "Radnik Kaleya APP",
            "Blokiranje termina po satu/danu/visednevno",
            "Instagram DM + TikTok DM",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS,
        "name": "Business",
        "monthly_price": 349,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 3,
        "max_staff_members": 5,
        "allow_sms": False,
        "allow_phone_calls": False,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": False,
        "description": "Za timove do 5 radnika.",
        "features": [
            "Sve iz Basic + Pro",
            "Do 5 radnika",
            "Radnik Kaleya APP za svakog radnika",
            "More languages by agreement",
            "API po klijentu",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS_PLUS,
        "name": "Business+",
        "monthly_price": 579,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 4,
        "max_staff_members": 15,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "Za vece timove do 15 radnika i glasovne kanale.",
        "features": [
            "Sve iz Basic + Pro + Business",
            "Do 15 radnika",
            "Telefonski pozivi i SMS",
            "ElevenLabs AI voice",
        ],
    },
    {
        "code": Plan.CODE_BUSINESS_PRO_PLUS,
        "name": "BusinessPro+",
        "monthly_price": 0,
        "currency": "USD",
        "trial_days": 14,
        "sort_order": 5,
        "is_contact_only": True,
        "max_staff_members": None,
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "Za 15+ radnika i custom integracije.",
        "features": [
            "Sve iz Basic + Pro + Business + Business+",
            "15+ radnika",
            "Custom integracije",
            "Napredna arhitektura po dogovoru",
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
        "allow_sms": True,
        "allow_phone_calls": True,
        "allow_instagram_dm": True,
        "allow_tiktok_dm": True,
        "allow_client_api_override": True,
        "allow_more_languages_by_agreement": True,
        "includes_elevenlabs_voice": True,
        "description": "Kupovina kompletnog projekta sa hostingom i domenom.",
        "features": ["Frontend", "Backend", "AI integracije", "Deploy priprema"],
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
