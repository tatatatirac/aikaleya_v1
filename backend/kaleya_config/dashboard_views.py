from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from django.views.decorators.http import require_POST

from ai_core.models import AlarmSettings, KaleyaCommandLog, VoiceSettings
from appointments.models import Appointment
from appointments.services import client_timezone, today_availability_summary
from billing.models import PaymentWebhookEvent, Plan, Subscription
from billing.services import enforce_staff_limit
from clients.models import BusinessClient, ClientApiSettings
from integrations.models import IntegrationConnection
from rest_framework.exceptions import ValidationError as DRFValidationError
from staff_services.models import BlockedTime, Service, StaffMember, WorkingHours


def is_admin_user(user):
    return user.is_staff or user.is_superuser or getattr(getattr(user, "profile", None), "role", None) == "admin"


def checkbox_value(post_data, key):
    return post_data.get(key) == "on"


def int_value(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def decimal_value(value, default):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return default


def dashboard_error_message(error):
    if isinstance(error, DjangoValidationError):
        if hasattr(error, "message_dict"):
            parts = []
            for field, messages_list in error.message_dict.items():
                parts.append(f"{field}: {', '.join(str(item) for item in messages_list)}")
            return "; ".join(parts)
        return "; ".join(str(item) for item in error.messages)

    detail = getattr(error, "detail", None)
    if detail:
        if isinstance(detail, dict):
            parts = []
            for field, messages_list in detail.items():
                if isinstance(messages_list, (list, tuple)):
                    parts.append(f"{field}: {', '.join(str(item) for item in messages_list)}")
                else:
                    parts.append(f"{field}: {messages_list}")
            return "; ".join(parts)
        if isinstance(detail, (list, tuple)):
            return "; ".join(str(item) for item in detail)
        return str(detail)

    return str(error)


def clients_for_user(user):
    queryset = BusinessClient.objects.select_related("owner", "subscription__plan").order_by("name")
    if is_admin_user(user):
        return queryset
    return queryset.filter(owner=user)


def get_client_subscription(client):
    try:
        return client.subscription
    except Subscription.DoesNotExist:
        return None


def ensure_business_working_hours(client):
    rows = []
    for weekday, _label in WorkingHours.WEEKDAY_CHOICES:
        row, _created = WorkingHours.objects.get_or_create(
            business_client=client,
            staff_member=None,
            weekday=weekday,
            defaults={
                "start_time": client.work_start,
                "end_time": client.work_end,
                "is_closed": weekday in {5, 6},
            },
        )
        rows.append(row)
    return rows


@require_POST
def dashboard_logout(request):
    logout(request)
    return redirect("/")


@login_required(login_url="/admin/login/")
def dashboard(request):
    clients = clients_for_user(request.user)
    selected_client = None

    selected_id = request.POST.get("client_id") or request.GET.get("client_id")
    if selected_id:
        selected_client = get_object_or_404(clients, id=selected_id)
    else:
        selected_client = clients.first()

    if selected_client is None:
        messages.warning(request, "Nema klijenta za ovaj nalog. Prvo kreiraj BusinessClient u Django adminu.")
        return render(request, "dashboard.html", {"clients": clients, "selected_client": None})

    api_settings, _ = ClientApiSettings.objects.get_or_create(business_client=selected_client)
    alarm_settings, _ = AlarmSettings.objects.get_or_create(business_client=selected_client)
    voice_settings, _ = VoiceSettings.objects.get_or_create(
        business_client=selected_client,
        defaults={"language": selected_client.voice_language},
    )

    if request.method == "POST":
        section = request.POST.get("section", "")
        detail_sections = {
            "add_staff",
            "update_staff",
            "delete_staff",
            "add_service",
            "update_service",
            "delete_service",
            "update_working_hours",
            "add_blocked_time",
            "delete_blocked_time",
        }
        if section in detail_sections:
            if not is_admin_user(request.user):
                messages.error(request, "Samo admin moze da menja radnike i usluge.")
                return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#client-detail")
            try:
                if section == "add_staff":
                    add_staff_member(request, selected_client)
                    messages.success(request, "Radnik je dodat.")
                elif section == "update_staff":
                    update_staff_member(request, selected_client)
                    messages.success(request, "Radnik je sacuvan.")
                elif section == "delete_staff":
                    delete_staff_member(request, selected_client)
                    messages.success(request, "Radnik je obrisan.")
                elif section == "add_service":
                    add_service(request, selected_client)
                    messages.success(request, "Usluga je dodata.")
                elif section == "update_service":
                    update_service(request, selected_client)
                    messages.success(request, "Usluga je sacuvana.")
                elif section == "delete_service":
                    delete_service(request, selected_client)
                    messages.success(request, "Usluga je obrisana.")
                elif section == "update_working_hours":
                    update_business_working_hours(request, selected_client)
                    messages.success(request, "Radno vreme je sacuvano.")
                elif section == "add_blocked_time":
                    add_blocked_time(request, selected_client)
                    messages.success(request, "Blokada termina je dodata.")
                elif section == "delete_blocked_time":
                    delete_blocked_time(request, selected_client)
                    messages.success(request, "Blokada termina je obrisana.")
            except (DjangoValidationError, DRFValidationError, ValueError) as error:
                messages.error(request, dashboard_error_message(error))
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#client-detail")
        if section == "client":
            update_client_settings(request, selected_client)
            messages.success(request, "Podešavanja klijenta su sačuvana.")
        elif section == "api" and is_admin_user(request.user):
            update_api_settings(request, api_settings)
            messages.success(request, "API podešavanja su sačuvana.")
        elif section == "voice":
            update_voice_settings(request, voice_settings)
            messages.success(request, "Podešavanja glasa su sačuvana.")
        elif section == "alarms":
            update_alarm_settings(request, alarm_settings)
            messages.success(request, "Alarm podešavanja klijenta su sačuvana.")
        elif section == "integrations":
            update_integrations(request, selected_client)
            messages.success(request, "Integracije su sačuvane.")
        elif section == "delete_client" and is_admin_user(request.user):
            client_name = str(selected_client)
            selected_client.delete()
            messages.success(request, f"Klijent {client_name} je obrisan.")
            return redirect(f"{reverse('dashboard')}#clients")
        elif section == "activate_client" and is_admin_user(request.user):
            update_client_subscription_state(selected_client, Subscription.STATUS_ACTIVE)
            messages.success(request, f"Klijent {selected_client} je aktiviran.")
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#clients")
        elif section == "pause_client" and is_admin_user(request.user):
            update_client_subscription_state(selected_client, Subscription.STATUS_PAST_DUE)
            messages.success(request, f"Klijent {selected_client} je pauziran.")
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#clients")
        elif section == "delete_client":
            messages.error(request, "Samo admin moze da obrise klijenta.")
        else:
            messages.error(request, "Nije moguće sačuvati ovu sekciju.")

        return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#{section or 'overview'}")

    integrations = ensure_integrations(selected_client)
    upcoming_appointments = (
        Appointment.objects.select_related("customer")
        .filter(business_client=selected_client)
        .exclude(status=Appointment.STATUS_CANCELLED)
        .order_by("date", "start_time")[:8]
    )
    cancelled_count = Appointment.objects.filter(
        business_client=selected_client,
        status=Appointment.STATUS_CANCELLED,
    ).count()
    today_summary = today_availability_summary(selected_client)
    selected_subscription = get_client_subscription(selected_client)
    selected_staff_members = selected_client.staff_members.all().order_by("full_name")
    selected_services = selected_client.services.all().order_by("category", "name")
    selected_working_hours = ensure_business_working_hours(selected_client)
    selected_blocked_times = (
        BlockedTime.objects.select_related("staff_member")
        .filter(business_client=selected_client)
        .order_by("-start_at")[:12]
    )
    selected_ai_logs = KaleyaCommandLog.objects.filter(business_client=selected_client).order_by("-created_at")[:8]
    selected_appointment_total = Appointment.objects.filter(business_client=selected_client).count()
    admin_has_full_access = is_admin_user(request.user)
    payment_webhook_events = PaymentWebhookEvent.objects.none()
    payment_webhook_total = 0
    payment_webhook_processed = 0
    payment_webhook_failed = 0
    payment_webhook_pending = 0
    if admin_has_full_access:
        payment_webhooks = PaymentWebhookEvent.objects.select_related("checkout", "checkout__plan")
        payment_webhook_events = payment_webhooks.order_by("-created_at")[:20]
        payment_webhook_total = payment_webhooks.count()
        payment_webhook_processed = payment_webhooks.filter(status=PaymentWebhookEvent.STATUS_PROCESSED).count()
        payment_webhook_failed = payment_webhooks.filter(status=PaymentWebhookEvent.STATUS_FAILED).count()
        payment_webhook_pending = payment_webhooks.filter(
            status__in=(PaymentWebhookEvent.STATUS_RECEIVED, PaymentWebhookEvent.STATUS_VERIFIED)
        ).count()

    context = {
        "is_admin_user": admin_has_full_access,
        "clients": clients,
        "selected_client": selected_client,
        "api_settings": api_settings,
        "alarm_settings": alarm_settings,
        "voice_settings": voice_settings,
        "integrations": integrations,
        "selected_subscription": selected_subscription,
        "selected_staff_members": selected_staff_members,
        "selected_services": selected_services,
        "selected_working_hours": selected_working_hours,
        "selected_blocked_times": selected_blocked_times,
        "selected_ai_logs": selected_ai_logs,
        "selected_appointment_total": selected_appointment_total,
        "upcoming_appointments": upcoming_appointments,
        "today_summary": today_summary,
        "cancelled_count": cancelled_count,
        "payment_webhook_events": payment_webhook_events,
        "payment_webhook_total": payment_webhook_total,
        "payment_webhook_processed": payment_webhook_processed,
        "payment_webhook_failed": payment_webhook_failed,
        "payment_webhook_pending": payment_webhook_pending,
        "language_choices": BusinessClient.LANGUAGE_CHOICES,
        "package_choices": BusinessClient.PACKAGE_CHOICES,
        "time_format_choices": BusinessClient.TIME_FORMAT_CHOICES,
        "date_format_choices": BusinessClient.DATE_FORMAT_CHOICES,
        "week_start_choices": BusinessClient.WEEK_START_CHOICES,
        "slot_choices": [15, 20, 30, 45, 60],
    }
    return render(request, "dashboard.html", context)


def update_client_subscription_state(client, status):
    plan = Plan.objects.filter(code=client.package, active=True).first() or Plan.objects.filter(code=Plan.CODE_BASIC).first()
    if plan is None:
        raise Plan.DoesNotExist("Nema plana za ovog klijenta.")

    now = timezone.now()
    defaults = {
        "plan": plan,
        "status": status,
        "trial_ends_at": None,
    }
    if status == Subscription.STATUS_ACTIVE:
        defaults.update(
            {
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
            }
        )
        client.kaleya_enabled = True
    else:
        defaults.update({"current_period_start": None, "current_period_end": None})
        client.kaleya_enabled = False

    Subscription.objects.update_or_create(business_client=client, defaults=defaults)
    client.save(update_fields=["kaleya_enabled", "updated_at"])


def add_staff_member(request, client):
    is_active = checkbox_value(request.POST, "is_active")
    if is_active:
        enforce_staff_limit(client)
    staff_member = StaffMember(
        business_client=client,
        full_name=request.POST.get("full_name", "").strip(),
        role_title=request.POST.get("role_title", "").strip(),
        phone=request.POST.get("phone", "").strip(),
        email=request.POST.get("email", "").strip(),
        color=request.POST.get("color", "#3b82f6").strip() or "#3b82f6",
        is_active=is_active,
    )
    staff_member.full_clean()
    staff_member.save()


def update_staff_member(request, client):
    staff_member = get_object_or_404(StaffMember, id=request.POST.get("staff_id"), business_client=client)
    was_inactive = not staff_member.is_active
    is_active = checkbox_value(request.POST, "is_active")
    if was_inactive and is_active:
        enforce_staff_limit(client)
    staff_member.full_name = request.POST.get("full_name", staff_member.full_name).strip() or staff_member.full_name
    staff_member.role_title = request.POST.get("role_title", "").strip()
    staff_member.phone = request.POST.get("phone", "").strip()
    staff_member.email = request.POST.get("email", "").strip()
    staff_member.color = request.POST.get("color", staff_member.color).strip() or staff_member.color
    staff_member.is_active = is_active
    staff_member.full_clean()
    staff_member.save()


def delete_staff_member(request, client):
    staff_member = get_object_or_404(StaffMember, id=request.POST.get("staff_id"), business_client=client)
    staff_member.delete()


def add_service(request, client):
    service = Service(
        business_client=client,
        name=request.POST.get("name", "").strip(),
        category=request.POST.get("category", "").strip(),
        duration_minutes=int_value(request.POST.get("duration_minutes"), 30),
        price=decimal_value(request.POST.get("price"), Decimal("0")),
        currency=request.POST.get("currency", "USD").strip() or "USD",
        is_active=checkbox_value(request.POST, "is_active"),
    )
    service.full_clean()
    service.save()


def update_service(request, client):
    service = get_object_or_404(Service, id=request.POST.get("service_id"), business_client=client)
    service.name = request.POST.get("name", service.name).strip() or service.name
    service.category = request.POST.get("category", "").strip()
    service.duration_minutes = int_value(request.POST.get("duration_minutes"), service.duration_minutes)
    service.price = decimal_value(request.POST.get("price"), service.price)
    service.currency = request.POST.get("currency", service.currency).strip() or service.currency
    service.is_active = checkbox_value(request.POST, "is_active")
    service.full_clean()
    service.save()


def delete_service(request, client):
    service = get_object_or_404(Service, id=request.POST.get("service_id"), business_client=client)
    service.delete()


def update_business_working_hours(request, client):
    for weekday, _label in WorkingHours.WEEKDAY_CHOICES:
        working_hours, _created = WorkingHours.objects.get_or_create(
            business_client=client,
            staff_member=None,
            weekday=weekday,
            defaults={"start_time": client.work_start, "end_time": client.work_end},
        )
        working_hours.start_time = parse_time(request.POST.get(f"weekday_{weekday}_start", "")) or working_hours.start_time
        working_hours.end_time = parse_time(request.POST.get(f"weekday_{weekday}_end", "")) or working_hours.end_time
        working_hours.is_closed = checkbox_value(request.POST, f"weekday_{weekday}_closed")
        working_hours.full_clean()
        working_hours.save()


def add_blocked_time(request, client):
    block_type = request.POST.get("block_type", "one_day")
    reason = request.POST.get("reason", "").strip()
    staff_id = request.POST.get("staff_id", "").strip()
    staff_member = None
    if staff_id:
        staff_member = get_object_or_404(StaffMember, id=staff_id, business_client=client)

    if block_type == "multi_day":
        start_date = parse_date(request.POST.get("start_date", ""))
        end_date = parse_date(request.POST.get("end_date", ""))
        if not start_date or not end_date:
            raise DjangoValidationError("Unesi datum od i datum do za visednevnu blokadu.")
        if end_date < start_date:
            raise DjangoValidationError("Datum do ne moze biti pre datuma od.")
        start_dt = timezone.make_aware(datetime.combine(start_date, time.min), timezone=client_timezone(client))
        end_dt = timezone.make_aware(datetime.combine(end_date, time.max), timezone=client_timezone(client))
    else:
        target_date = parse_date(request.POST.get("block_date", ""))
        start_time = parse_time(request.POST.get("start_time", ""))
        end_time = parse_time(request.POST.get("end_time", ""))
        if not target_date or not start_time or not end_time:
            raise DjangoValidationError("Unesi datum i vreme od-do za jednodnevnu blokadu.")
        start_dt = timezone.make_aware(datetime.combine(target_date, start_time), timezone=client_timezone(client))
        end_dt = timezone.make_aware(datetime.combine(target_date, end_time), timezone=client_timezone(client))

    blocked_time = BlockedTime(
        business_client=client,
        staff_member=staff_member,
        start_at=start_dt,
        end_at=end_dt,
        reason=reason,
        source="admin_dashboard",
    )
    blocked_time.full_clean()
    blocked_time.save()


def delete_blocked_time(request, client):
    blocked_time = get_object_or_404(BlockedTime, id=request.POST.get("blocked_time_id"), business_client=client)
    blocked_time.delete()


def update_client_settings(request, client):
    post = request.POST
    work_start = parse_time(post.get("work_start", ""))
    work_end = parse_time(post.get("work_end", ""))

    client.name = post.get("name", client.name).strip() or client.name
    client.public_name = post.get("public_name", "").strip()
    client.package = post.get("package", client.package)
    client.language = post.get("language", client.language)
    client.interface_language = post.get("interface_language", client.interface_language)
    client.voice_language = post.get("voice_language", client.voice_language)
    client.timezone = post.get("timezone", client.timezone).strip() or client.timezone
    client.kaleya_enabled = checkbox_value(post, "kaleya_enabled")
    client.work_start = work_start or client.work_start
    client.work_end = work_end or client.work_end
    client.slot_interval_minutes = int_value(post.get("slot_interval_minutes"), client.slot_interval_minutes)
    client.time_format = post.get("time_format", client.time_format)
    client.date_format = post.get("date_format", client.date_format)
    client.week_start = int_value(post.get("week_start"), client.week_start)
    client.allow_phone_calls = checkbox_value(post, "allow_phone_calls")
    client.allow_sms = checkbox_value(post, "allow_sms")
    client.allow_whatsapp = checkbox_value(post, "allow_whatsapp")
    client.allow_viber = checkbox_value(post, "allow_viber")
    client.allow_telegram = checkbox_value(post, "allow_telegram")
    client.full_clean()
    client.save()


def update_api_settings(request, api_settings):
    post = request.POST
    api_settings.ai_provider = post.get("ai_provider", api_settings.ai_provider).strip() or api_settings.ai_provider
    api_settings.ai_model = post.get("ai_model", api_settings.ai_model).strip() or api_settings.ai_model
    api_settings.voice_provider = post.get("voice_provider", api_settings.voice_provider).strip() or api_settings.voice_provider
    api_settings.voice_model = post.get("voice_model", api_settings.voice_model).strip()
    api_settings.voice_id = post.get("voice_id", api_settings.voice_id).strip()

    ai_api_key = post.get("ai_api_key", "").strip()
    voice_api_key = post.get("voice_api_key", "").strip()
    if ai_api_key:
        api_settings.ai_api_key = ai_api_key
    if voice_api_key:
        api_settings.voice_api_key = voice_api_key

    api_settings.save()


def update_voice_settings(request, voice_settings):
    post = request.POST
    voice_settings.language = post.get("voice_language", voice_settings.language)
    voice_settings.voice_id = post.get("voice_id", voice_settings.voice_id).strip()
    voice_settings.speed = post.get("speed", voice_settings.speed)
    voice_settings.stability = post.get("stability", voice_settings.stability)
    voice_settings.similarity_boost = post.get("similarity_boost", voice_settings.similarity_boost)
    voice_settings.save()


def update_alarm_settings(request, alarm_settings):
    post = request.POST
    alarm_settings.notifications_enabled = checkbox_value(post, "notifications_enabled")
    alarm_settings.urgent_enabled = checkbox_value(post, "urgent_enabled")
    alarm_settings.announcement_enabled = checkbox_value(post, "announcement_enabled")
    alarm_settings.notification_sound = post.get("notification_sound", alarm_settings.notification_sound).strip()
    alarm_settings.urgent_sound = post.get("urgent_sound", alarm_settings.urgent_sound).strip()
    alarm_settings.announcement_sound = post.get("announcement_sound", alarm_settings.announcement_sound).strip()
    alarm_settings.notification_volume = int_value(post.get("notification_volume"), alarm_settings.notification_volume)
    alarm_settings.urgent_volume = int_value(post.get("urgent_volume"), alarm_settings.urgent_volume)
    alarm_settings.announcement_volume = int_value(post.get("announcement_volume"), alarm_settings.announcement_volume)
    alarm_settings.save()


def ensure_integrations(client):
    providers = ("whatsapp", "viber", "telegram", "sms", "phone")
    integrations = []
    for provider in providers:
        integration, _ = IntegrationConnection.objects.get_or_create(
            business_client=client,
            provider=provider,
            defaults={"enabled": False, "status": "draft"},
        )
        integrations.append(integration)
    return integrations


def update_integrations(request, client):
    for integration in ensure_integrations(client):
        prefix = f"integration_{integration.provider}"
        integration.enabled = checkbox_value(request.POST, f"{prefix}_enabled")
        integration.status = request.POST.get(f"{prefix}_status", integration.status)
        integration.public_number = request.POST.get(f"{prefix}_public_number", integration.public_number).strip()
        integration.webhook_url = request.POST.get(f"{prefix}_webhook_url", integration.webhook_url).strip()
        integration.save()
