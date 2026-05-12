from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ai_core.models import AlarmSettings, VoiceSettings
from appointments.models import Appointment, Customer
from billing.models import CheckoutSession, PaymentWebhookEvent, PendingCheckoutRegistration, Plan, Subscription
from clients.models import BusinessClient, ClientApiSettings
from integrations.models import IntegrationConnection
from staff_services.models import Service, StaffMember, StaffService, WorkingHours


TEMPLATE_CLIENTS = [
    {
        "email": "basic-template@aikaleya.com",
        "company": "Kaleya Basic Firma",
        "public_name": "Basic Template Salon",
        "full_name": "Basic Template Owner",
        "phone": "+381 60 100 0001",
        "plan_code": Plan.CODE_BASIC,
        "staff": [],
        "services": [
            {"name": "Sisanje", "category": "Salon", "duration": 30, "price": 25},
            {"name": "AI zakazivanje", "category": "Osnovno", "duration": 30, "price": 59},
            {"name": "Konsultacija", "category": "Osnovno", "duration": 30, "price": 25},
        ],
        "integrations": ("whatsapp", "viber", "telegram"),
    },
    {
        "email": "business-template@aikaleya.com",
        "company": "Kaleya Business Firma",
        "public_name": "Business Template Clinic",
        "full_name": "Business Template Owner",
        "phone": "+381 60 100 0002",
        "plan_code": Plan.CODE_BUSINESS,
        "staff": [
            {"name": "Ana Markovic", "role": "Senior specialist", "phone": "+381 60 210 0001", "color": "#14b8a6"},
            {"name": "Nikola Petrovic", "role": "Specialist", "phone": "+381 60 210 0002", "color": "#3487f5"},
            {"name": "Milica Jovanovic", "role": "Assistant", "phone": "+381 60 210 0003", "color": "#a855f7"},
        ],
        "services": [
            {"name": "Pregled", "category": "Usluge", "duration": 30, "price": 45},
            {"name": "Tretman", "category": "Usluge", "duration": 60, "price": 90},
            {"name": "Kontrola", "category": "Usluge", "duration": 30, "price": 35},
        ],
        "integrations": ("whatsapp", "viber", "telegram", "instagram", "tiktok"),
    },
    {
        "email": "business-plus-template@aikaleya.com",
        "company": "Kaleya Business+ Firma",
        "public_name": "Business+ Template Center",
        "full_name": "Business Plus Template Owner",
        "phone": "+381 60 100 0003",
        "plan_code": Plan.CODE_BUSINESS_PLUS,
        "staff": [
            {"name": "Jelena Ilic", "role": "Manager", "phone": "+381 60 310 0001", "color": "#14b8a6"},
            {"name": "Marko Simic", "role": "Lead specialist", "phone": "+381 60 310 0002", "color": "#3487f5"},
            {"name": "Ivana Nikolic", "role": "Specialist", "phone": "+381 60 310 0003", "color": "#f59e0b"},
            {"name": "Stefan Pavlovic", "role": "Specialist", "phone": "+381 60 310 0004", "color": "#a855f7"},
            {"name": "Tamara Kostic", "role": "Assistant", "phone": "+381 60 310 0005", "color": "#ef4444"},
            {"name": "Luka Popovic", "role": "Coordinator", "phone": "+381 60 310 0006", "color": "#22c55e"},
        ],
        "services": [
            {"name": "Premium pregled", "category": "Premium", "duration": 30, "price": 75},
            {"name": "Premium tretman", "category": "Premium", "duration": 60, "price": 140},
            {"name": "Dugi termin", "category": "Premium", "duration": 120, "price": 240},
            {"name": "Kontrola", "category": "Premium", "duration": 30, "price": 50},
        ],
        "integrations": ("whatsapp", "viber", "telegram", "sms", "phone", "email", "google_calendar", "instagram", "tiktok"),
    },
]


class Command(BaseCommand):
    help = "Creates three paid template companies: Basic, Business and Business+."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_plans", verbosity=0)

        template_emails = [item["email"] for item in TEMPLATE_CLIENTS]

        PaymentWebhookEvent.objects.all().delete()
        PendingCheckoutRegistration.objects.all().delete()
        CheckoutSession.objects.all().delete()

        deleted_clients, _details = BusinessClient.objects.exclude(owner__email__in=template_emails).delete()

        created_clients = []
        for template in TEMPLATE_CLIENTS:
            created_clients.append(self.create_template_client(template))

        self.stdout.write(self.style.SUCCESS("Kaleya paid template companies are ready."))
        self.stdout.write(f"Deleted non-template objects: {deleted_clients}")
        for client in created_clients:
            self.stdout.write(f"- {client.public_name or client.name}: {client.get_package_display()} / paid active")

    def create_template_client(self, template):
        plan = Plan.objects.get(code=template["plan_code"])
        user = self.upsert_owner(template)
        client, _created = BusinessClient.objects.update_or_create(
            owner=user,
            defaults={
                "name": template["company"],
                "public_name": template["public_name"],
                "package": plan.code,
                "language": "en",
                "interface_language": "en",
                "voice_language": "en",
                "timezone": "Europe/Belgrade",
                "is_demo": False,
                "kaleya_enabled": True,
                "work_start": time(9, 0),
                "work_end": time(16, 0),
                "slot_interval_minutes": 30,
                "time_format": "24h",
                "date_format": "dd-mm-yyyy",
                "week_start": 0,
                "allow_phone_calls": plan.allow_phone_calls,
                "allow_sms": plan.allow_sms,
                "allow_whatsapp": plan.allow_whatsapp,
                "allow_viber": plan.allow_viber,
                "allow_telegram": plan.allow_telegram,
            },
        )

        user.profile.role = "client"
        user.profile.business_client = client
        user.profile.phone = template["phone"]
        user.profile.save(update_fields=["role", "business_client", "phone", "updated_at"])

        ClientApiSettings.objects.update_or_create(
            business_client=client,
            defaults={
                "ai_provider": "anthropic",
                "ai_model": "claude-haiku-4-5-20251001",
                "voice_provider": "elevenlabs",
                "voice_model": "eleven_multilingual_v2",
                "voice_id": getattr(settings, "KALEYA_ELEVENLABS_VOICE_ID", ""),
            },
        )
        VoiceSettings.objects.update_or_create(
            business_client=client,
            defaults={
                "language": client.voice_language,
                "voice_id": getattr(settings, "KALEYA_ELEVENLABS_VOICE_ID", ""),
                "speed": 1.00,
                "stability": 0.50,
                "similarity_boost": 0.75,
            },
        )
        AlarmSettings.objects.get_or_create(business_client=client)

        Subscription.objects.update_or_create(
            business_client=client,
            defaults={
                "plan": plan,
                "status": Subscription.STATUS_ACTIVE,
                "trial_ends_at": None,
                "current_period_start": timezone.now(),
                "current_period_end": timezone.now() + timedelta(days=30),
                "external_customer_id": f"template-customer-{plan.code}",
                "external_subscription_id": f"template-subscription-{plan.code}",
            },
        )

        self.rebuild_operations_data(client, template)
        self.create_paid_checkout_log(client, template, plan)
        return client

    def upsert_owner(self, template):
        email = template["email"].lower()
        first_name, last_name = template["full_name"].split(" ", 1)
        user = User.objects.filter(email__iexact=email).first() or User.objects.filter(username__iexact=email).first()
        if user is None:
            user = User(username=email, email=email)
        user.username = email
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False
        user.set_password("KaleyaTemplate123!")
        user.save()
        return user

    def rebuild_operations_data(self, client, template):
        client.appointments.all().delete()
        client.customers.all().delete()
        client.working_hours.all().delete()
        client.staff_members.all().delete()
        client.services.all().delete()
        client.integrations.all().delete()

        for weekday in range(5):
            WorkingHours.objects.create(
                business_client=client,
                weekday=weekday,
                start_time=time(9, 0),
                end_time=time(16, 0),
                is_closed=False,
            )

        services = []
        for service_data in template["services"]:
            services.append(
                Service.objects.create(
                    business_client=client,
                    name=service_data["name"],
                    category=service_data["category"],
                    duration_minutes=service_data["duration"],
                    price=service_data["price"],
                    currency="USD",
                    is_active=True,
                )
            )

        staff_members = []
        for staff_data in template["staff"]:
            staff_member = StaffMember.objects.create(
                business_client=client,
                full_name=staff_data["name"],
                role_title=staff_data["role"],
                phone=staff_data["phone"],
                color=staff_data["color"],
                is_active=True,
            )
            staff_members.append(staff_member)
            for weekday in range(5):
                WorkingHours.objects.create(
                    business_client=client,
                    staff_member=staff_member,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(16, 0),
                    is_closed=False,
                )
            for service in services:
                StaffService.objects.create(staff_member=staff_member, service=service, is_active=True)

        self.create_integrations(client, template)
        self.create_appointments(client, services, staff_members)

    def create_integrations(self, client, template):
        enabled_providers = set(template["integrations"])
        for provider, _label in IntegrationConnection.PROVIDER_CHOICES:
            IntegrationConnection.objects.create(
                business_client=client,
                provider=provider,
                enabled=provider in enabled_providers,
                status="connected" if provider in enabled_providers else "draft",
                public_number=client.owner.profile.phone if provider in {"whatsapp", "viber", "telegram", "sms", "phone"} else "",
                webhook_url=f"https://aikaleya.com/api/integrations/{provider}/webhook/" if provider in enabled_providers else "",
            )

    def create_appointments(self, client, services, staff_members):
        today = timezone.localdate()
        customers = [
            Customer.objects.create(
                business_client=client,
                first_name="Milan",
                last_name="Jankovic",
                phone="+381 64 123 4567",
                preferred_channel="phone",
            ),
            Customer.objects.create(
                business_client=client,
                first_name="Sofija",
                last_name="Nikolic",
                phone="+381 63 987 6543",
                preferred_channel="whatsapp",
            ),
            Customer.objects.create(
                business_client=client,
                first_name="Petar",
                last_name="Ilic",
                phone="+381 61 555 333",
                preferred_channel="telegram",
            ),
        ]
        appointment_rows = [
            (today, time(10, 0), Appointment.STATUS_CONFIRMED, customers[0], "phone"),
            (today + timedelta(days=1), time(11, 30), Appointment.STATUS_MOVED, customers[1], "whatsapp"),
            (today + timedelta(days=2), time(14, 0), Appointment.STATUS_CANCELLED, customers[2], "telegram"),
        ]
        for index, (date_value, start, status, customer, channel) in enumerate(appointment_rows):
            service = services[index % len(services)] if services else None
            staff_member = staff_members[index % len(staff_members)] if staff_members else None
            Appointment.objects.create(
                business_client=client,
                customer=customer,
                staff_member=staff_member,
                service=service,
                title=service.name if service else "Termin",
                status=status,
                date=date_value,
                start_time=start,
                duration_minutes=service.duration_minutes if service else 30,
                channel=channel,
                source="template_seed",
                notes="Template paid company appointment.",
            )

    def create_paid_checkout_log(self, client, template, plan):
        checkout = CheckoutSession.objects.create(
            business_client=client,
            plan=plan,
            provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
            status=CheckoutSession.STATUS_PAID,
            email=template["email"],
            company=template["company"],
            full_name=template["full_name"],
            amount=plan.monthly_price,
            currency=plan.currency,
            trial_days=plan.trial_days,
            checkout_url="https://aikaleya.lemonsqueezy.com/checkout/template",
            external_checkout_id=f"template-checkout-{plan.code}",
            metadata={"template": True, "plan_code": plan.code},
        )
        PaymentWebhookEvent.objects.create(
            provider=CheckoutSession.PROVIDER_LEMONSQUEEZY,
            event_name="subscription_created",
            external_event_id=f"template-event-{plan.code}",
            external_object_id=f"template-subscription-{plan.code}",
            checkout=checkout,
            status=PaymentWebhookEvent.STATUS_PROCESSED,
            signature_valid=True,
            payload={
                "template": True,
                "plan_code": plan.code,
                "company": template["company"],
                "status": "paid",
            },
            processed_at=timezone.now(),
        )
