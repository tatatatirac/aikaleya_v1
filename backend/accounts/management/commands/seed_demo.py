import os
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_core.models import AlarmSettings, GlobalAISettings, VoiceSettings
from appointments.models import Appointment, Customer
from billing.models import Plan, Subscription
from clients.models import BusinessClient, ClientApiSettings
from integrations.models import IntegrationConnection
from notifications.models import NotificationRule
from staff_services.models import Service, StaffMember, StaffService, WorkingHours


class Command(BaseCommand):
    help = "Creates local demo data for Kaleya development."

    def handle(self, *args, **options):
        admin_email = os.environ.get("KALEYA_DEMO_ADMIN_EMAIL", "admin@aikaleya.com").strip().lower()
        admin_password = os.environ.get("KALEYA_DEMO_ADMIN_PASSWORD", "admin123")
        client_email = os.environ.get("KALEYA_DEMO_CLIENT_EMAIL", "administrator@test.com").strip().lower()
        employee_email = os.environ.get("KALEYA_DEMO_EMPLOYEE_EMAIL", "employee@test.com").strip().lower()
        employee_username = os.environ.get("KALEYA_DEMO_EMPLOYEE_USERNAME", "employee").strip().lower()
        self.rename_user_email("admin@aikaleya.com", admin_email)
        self.rename_user_email("klijent@test.com", client_email)
        self.rename_user_email("empl@test.com", employee_email)

        admin = self.create_user(
            email=admin_email,
            password=admin_password,
            is_staff=True,
            is_superuser=True,
            first_name="Kaleya",
            last_name="Admin",
        )
        client_user = self.create_user(
            email=client_email,
            password="test123",
            first_name="Demo",
            last_name="Client",
        )
        employee_user = self.create_user(
            email=employee_email,
            password="emp123",
            first_name="Employee",
            last_name="Employee",
        )
        username_taken = User.objects.filter(username__iexact=employee_username).exclude(id=employee_user.id).exists()
        if employee_user.username != employee_username and not username_taken:
            employee_user.username = employee_username
            employee_user.save(update_fields=["username"])

        client, _created = BusinessClient.objects.update_or_create(
            owner=client_user,
            name="Demo Administrator",
            defaults={
                "public_name": "Kaleya Demo Administrator",
                "package": BusinessClient.PACKAGE_BUSINESS,
                "language": "en",
                "interface_language": "en",
                "voice_language": "en",
                "timezone": "Europe/Belgrade",
                "is_demo": True,
                "kaleya_enabled": True,
                "work_start": time(9, 0),
                "work_end": time(16, 0),
                "slot_interval_minutes": 30,
                "time_format": "24h",
                "date_format": "dd-mm-yyyy",
                "week_start": 0,
            },
        )

        client_user.profile.role = "client"
        client_user.profile.business_client = client
        client_user.profile.phone = "+1 555 0100"
        client_user.profile.save(update_fields=["role", "business_client", "phone", "updated_at"])

        employee_user.profile.role = "employee"
        employee_user.profile.business_client = client
        employee_user.profile.phone = "+1 555 0177"
        employee_user.profile.save(update_fields=["role", "business_client", "phone", "updated_at"])

        ClientApiSettings.objects.update_or_create(
            business_client=client,
            defaults={
                "ai_provider": "anthropic",
                "ai_model": "claude-haiku-4-5-20251001",
                "voice_provider": "elevenlabs",
                "voice_model": "eleven_multilingual_v2",
            },
        )
        VoiceSettings.objects.get_or_create(
            business_client=client,
            defaults={"language": "en", "voice_id": "demo-voice"},
        )
        AlarmSettings.objects.get_or_create(business_client=client)
        GlobalAISettings.objects.update_or_create(
            id=1,
            defaults={
                "ai_provider": "anthropic",
                "ai_model": "claude-haiku-4-5-20251001",
                "voice_provider": "elevenlabs",
                "voice_model": "eleven_multilingual_v2",
                "enabled": True,
            },
        )

        self.create_plans()
        business_plan = Plan.objects.get(code=Plan.CODE_BUSINESS_PLUS)
        client.package = Plan.CODE_BUSINESS_PLUS
        client.save(update_fields=["package", "updated_at"])
        Subscription.objects.update_or_create(
            business_client=client,
            defaults={
                "plan": business_plan,
                "status": Subscription.STATUS_TRIAL,
                "trial_ends_at": timezone.now() + timedelta(days=14),
            },
        )

        for provider in ("whatsapp", "viber", "telegram", "sms", "phone", "email", "google_calendar"):
            IntegrationConnection.objects.get_or_create(
                business_client=client,
                provider=provider,
                defaults={"enabled": False, "status": "draft"},
            )

        self.create_demo_calendar(client, employee_user)
        self.create_notification_rules(client)

        self.stdout.write(self.style.SUCCESS("Kaleya demo backend podaci su spremni."))
        self.stdout.write(f"Admin login: {admin_email} / vrednost iz KALEYA_DEMO_ADMIN_PASSWORD")
        self.stdout.write(f"Administrator app login: {client_email} / test123")
        self.stdout.write(f"Employee login: {employee_username} / emp123")

    def rename_user_email(self, old_email, new_email):
        if old_email.lower() == new_email.lower():
            return
        if User.objects.filter(email__iexact=new_email).exists():
            return
        user = User.objects.filter(email__iexact=old_email.lower()).first()
        if not user:
            return
        user.email = new_email
        user.username = new_email
        user.save(update_fields=["email", "username"])

    def create_user(self, email, password, **defaults):
        user = User.objects.filter(email__iexact=email.lower()).first()
        created = False
        if user is None:
            user, created = User.objects.get_or_create(
                username=email.lower(),
                defaults={"email": email.lower(), **defaults},
            )
        user.set_password(password)
        if created:
            user.save()
        else:
            changed = False
            for field, value in defaults.items():
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True
            if user.email != email.lower():
                user.email = email.lower()
                changed = True
            if changed:
                user.save()
            else:
                user.save(update_fields=["password"])
        return user

    def create_plans(self):
        plans = [
            {
                "code": Plan.CODE_BASIC,
                "name": "Starter",
                "monthly_price": 59,
                "currency": "USD",
                "sort_order": 1,
                "max_staff_members": 0,
                "allow_sms": False,
                "allow_phone_calls": False,
                "allow_instagram_dm": False,
                "allow_tiktok_dm": False,
                "allow_client_api_override": False,
                "allow_more_languages_by_agreement": False,
                "includes_elevenlabs_voice": False,
                "description": "AI Kaleya za vlasnika i osnovne komunikacione kanale.",
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
                "monthly_price": 89,
                "currency": "USD",
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

        for plan in plans:
            Plan.objects.update_or_create(code=plan["code"], defaults=plan)

    def create_demo_calendar(self, client, employee_user):
        Appointment.objects.filter(business_client=client).delete()
        Customer.objects.filter(business_client=client).delete()
        StaffService.objects.filter(staff_member__business_client=client).delete()
        WorkingHours.objects.filter(business_client=client).delete()
        StaffMember.objects.filter(business_client=client).delete()
        Service.objects.filter(business_client=client).delete()

        staff = StaffMember.objects.create(
            business_client=client,
            full_name="Mark Johnson",
            role_title="Senior Specialist",
            phone="+1 555 0199",
            email="mark@example.com",
            color="#14b8a6",
        )
        employee_staff = StaffMember.objects.create(
            business_client=client,
            user=employee_user,
            full_name="Employee User",
            role_title="Receptionist",
            phone="+1 555 0177",
            email=employee_user.email,
            color="#3b82f6",
        )
        services = [
            Service.objects.create(
                business_client=client,
                name="Standard appointment",
                category="General",
                duration_minutes=30,
                price=40,
                currency="USD",
            ),
            Service.objects.create(
                business_client=client,
                name="Extended appointment",
                category="General",
                duration_minutes=60,
                price=75,
                currency="USD",
            ),
        ]
        for service in services:
            StaffService.objects.create(staff_member=staff, service=service)
            StaffService.objects.create(staff_member=employee_staff, service=service)

        for weekday in range(5):
            WorkingHours.objects.create(
                business_client=client,
                staff_member=staff,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(16, 0),
            )
            WorkingHours.objects.create(
                business_client=client,
                staff_member=employee_staff,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(16, 0),
            )

        customers = [
            Customer.objects.create(
                business_client=client,
                first_name="Michael",
                last_name="Johnson",
                phone="+1 555 0101",
                preferred_channel="phone",
            ),
            Customer.objects.create(
                business_client=client,
                first_name="Emily",
                last_name="Carter",
                phone="+1 555 0102",
                preferred_channel="whatsapp",
            ),
            Customer.objects.create(
                business_client=client,
                first_name="Daniel",
                last_name="Miller",
                phone="+1 555 0103",
                preferred_channel="sms",
            ),
        ]

        today = date.today()
        Appointment.objects.create(
            business_client=client,
            customer=customers[0],
            staff_member=staff,
            service=services[0],
            status=Appointment.STATUS_CONFIRMED,
            date=today,
            start_time=time(9, 0),
            duration_minutes=30,
            channel="phone",
            source="demo",
        )
        Appointment.objects.create(
            business_client=client,
            customer=customers[1],
            staff_member=staff,
            service=services[1],
            status=Appointment.STATUS_MOVED,
            date=today,
            start_time=time(11, 0),
            duration_minutes=60,
            channel="whatsapp",
            source="demo",
        )
        Appointment.objects.create(
            business_client=client,
            customer=customers[2],
            staff_member=employee_staff,
            service=services[0],
            status=Appointment.STATUS_CONFIRMED,
            date=today,
            start_time=time(13, 0),
            duration_minutes=30,
            channel="phone",
            source="demo",
        )
        Appointment.objects.create(
            business_client=client,
            customer=customers[2],
            staff_member=staff,
            service=services[0],
            status=Appointment.STATUS_CANCELLED,
            date=today + timedelta(days=1),
            start_time=time(10, 30),
            duration_minutes=30,
            channel="sms",
            source="demo",
            cancelled_reason="Demo cancellation",
        )
        Appointment.objects.create(
            business_client=client,
            staff_member=staff,
            title="Blocked for staff meeting",
            status=Appointment.STATUS_BLOCKED,
            date=today + timedelta(days=2),
            start_time=time(14, 0),
            duration_minutes=120,
            channel="web",
            source="demo",
        )

    def create_notification_rules(self, client):
        NotificationRule.objects.filter(business_client=client).delete()
        rules = [
            ("appointment_created", "whatsapp", 0),
            ("appointment_changed", "sms", 0),
            ("appointment_cancelled", "sms", 0),
            ("reminder_before", "whatsapp", -1440),
            ("reminder_before", "sms", -120),
            ("support_needed", "dashboard", 0),
            ("daily_report", "email", 0),
        ]
        for event, channel, offset_minutes in rules:
            NotificationRule.objects.create(
                business_client=client,
                event=event,
                channel=channel,
                offset_minutes=offset_minutes,
                language=client.interface_language,
            )
