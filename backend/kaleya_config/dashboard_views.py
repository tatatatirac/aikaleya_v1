from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_time

from ai_core.models import AlarmSettings, VoiceSettings
from appointments.models import Appointment
from appointments.services import today_availability_summary
from clients.models import BusinessClient, ClientApiSettings
from integrations.models import IntegrationConnection


def is_admin_user(user):
    return user.is_staff or user.is_superuser or getattr(getattr(user, "profile", None), "role", None) == "admin"


def checkbox_value(post_data, key):
    return post_data.get(key) == "on"


def int_value(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clients_for_user(user):
    queryset = BusinessClient.objects.select_related("owner").order_by("name")
    if is_admin_user(user):
        return queryset
    return queryset.filter(owner=user)


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

    context = {
        "is_admin_user": is_admin_user(request.user),
        "clients": clients,
        "selected_client": selected_client,
        "api_settings": api_settings,
        "alarm_settings": alarm_settings,
        "voice_settings": voice_settings,
        "integrations": integrations,
        "upcoming_appointments": upcoming_appointments,
        "today_summary": today_summary,
        "cancelled_count": cancelled_count,
        "language_choices": BusinessClient.LANGUAGE_CHOICES,
        "package_choices": BusinessClient.PACKAGE_CHOICES,
        "time_format_choices": BusinessClient.TIME_FORMAT_CHOICES,
        "date_format_choices": BusinessClient.DATE_FORMAT_CHOICES,
        "week_start_choices": BusinessClient.WEEK_START_CHOICES,
        "slot_choices": [15, 20, 30, 45, 60],
    }
    return render(request, "dashboard.html", context)


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
