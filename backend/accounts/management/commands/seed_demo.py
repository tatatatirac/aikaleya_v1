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
        admin = self.create_user(
            email="admin@aikaleya.com",
            password="admin123",
            is_staff=True,
            is_superuser=True,
            first_name="Kaleya",
            last_name="Admin",
        )
        client_user = self.create_user(
            email="klijent@test.com",
            password="test123",
            first_name="Demo",
            last_name="Client",
        )

        client, _created = BusinessClient.objects.update_or_create(
            owner=client_user,
            name="Demo Client",
            defaults={
                "public_name": "Kaleya Demo Client",
                "package": BusinessClient.PACKAGE_PRO,
                "language": "en",
                "interface_language": "en",
                "voice_language": "en",
                "timezone": "Europe/Belgrade",
                "kaleya_enabled": True,
                "work_start": time(9, 0),
                "work_end": time(16, 0),
                "slot_interval_minutes": 30,
                "time_format": "24h",
                "week_start": 0,
            },
        )

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
        pro_plan = Plan.objects.get(code=Plan.CODE_PRO)
        Subscription.objects.get_or_create(
            business_client=client,
            defaults={
                "plan": pro_plan,
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

        self.create_demo_calendar(client)
        self.create_notification_rules(client)

        self.stdout.write(self.style.SUCCESS("Kaleya demo backend podaci su spremni."))
        self.stdout.write("Admin login: admin@aikaleya.com / admin123")
        self.stdout.write("Client login: klijent@test.com / test123")

    def create_user(self, email, password, **defaults):
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
                "name": "Basic",
                "monthly_price": 49,
                "sort_order": 1,
                "description": "Starter paket za male timove.",
                "features": ["AI zakazivanje", "Kalendar", "Osnovni kanali"],
            },
            {
                "code": Plan.CODE_PRO,
                "name": "Pro",
                "monthly_price": 99,
                "sort_order": 2,
                "description": "Napredni paket za aktivne biznise.",
                "features": ["Sve iz Basic", "Glas", "Alarmi", "Integracije"],
            },
            {
                "code": Plan.CODE_BUSINESS,
                "name": "Business",
                "monthly_price": 199,
                "sort_order": 3,
                "description": "Paket za vise lokacija i veci obim.",
                "features": ["Sve iz Pro", "Prioritet", "Napredni modeli"],
            },
            {
                "code": Plan.CODE_GOD_MODE,
                "name": "GOD MODE",
                "monthly_price": 0,
                "sort_order": 4,
                "is_contact_only": True,
                "description": "Kupovina kompletnog projekta sa hostingom i domenom.",
                "features": ["Frontend", "Backend", "AI integracije", "Deploy priprema"],
            },
        ]

        for plan in plans:
            Plan.objects.update_or_create(code=plan["code"], defaults=plan)

    def create_demo_calendar(self, client):
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

        for weekday in range(5):
            WorkingHours.objects.create(
                business_client=client,
                staff_member=staff,
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
