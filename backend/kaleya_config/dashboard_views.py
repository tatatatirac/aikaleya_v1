import re
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout
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
from communications.models import CallSession, Conversation
from integrations.models import IntegrationConnection
from rest_framework.exceptions import ValidationError as DRFValidationError
from staff_services.models import BlockedTime, Service, StaffMember, WorkingHours
from support.models import SupportTicket


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


def dashboard_section_anchor(section):
    return {
        "client": "settings",
        "api": "settings",
        "voice": "settings",
        "alarms": "alarms",
        "integrations": "integrations",
        "telegram_integration": "integrations",
        "whatsapp_integration": "integrations",
        "viber_integration": "integrations",
        "instagram_integration": "integrations",
        "provision_phone": "integrations",
        "release_phone": "integrations",
    }.get(section or "overview", section or "overview")


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


def support_requester_label(ticket):
    metadata = ticket.metadata or {}
    payload = metadata.get("payload") or {}
    parts = [
        metadata.get("requester_name") or payload.get("customer_name") or payload.get("name") or "",
        metadata.get("requester_phone") or payload.get("phone") or payload.get("customer_phone") or "",
        metadata.get("requester_email") or payload.get("email") or payload.get("customer_email") or "",
    ]
    return " - ".join(part for part in parts if part)


def build_conversation_feed(client):
    feed = []
    conversations = (
        Conversation.objects.select_related("customer")
        .prefetch_related("messages")
        .filter(business_client=client)
        .order_by("-last_message_at", "-created_at")[:12]
    )
    for conversation in conversations:
        messages = list(conversation.messages.all())
        last_message = messages[-1] if messages else None
        customer = conversation.customer
        metadata = conversation.metadata or {}
        customer_name = (
            getattr(customer, "full_name", "")
            or metadata.get("customer_name")
            or metadata.get("name")
            or "Nepoznat klijent"
        )
        customer_phone = getattr(customer, "phone", "") or metadata.get("phone") or metadata.get("customer_phone") or ""
        status_group = "urgent" if conversation.status == "handoff" else "resolved" if conversation.status == "closed" else "unresolved"
        feed.append(
            {
                "kind": "conversation",
                "conversation_id": conversation.id,
                "channel": conversation.channel,
                "filter": status_group,
                "title": f"{customer_name} - {conversation.get_channel_display()}",
                "subtitle": last_message.body if last_message else "Razgovor nema sacuvanih poruka.",
                "contact": customer_phone or conversation.get_status_display(),
                "status": conversation.get_status_display(),
                "created_at": conversation.last_message_at or conversation.created_at,
                "urgent": conversation.status == "handoff",
            }
        )

    tickets = SupportTicket.objects.filter(business_client=client).order_by("-created_at")[:12]
    for ticket in tickets:
        closed = ticket.status in (SupportTicket.STATUS_RESOLVED, SupportTicket.STATUS_CLOSED)
        urgent = ticket.priority == SupportTicket.PRIORITY_URGENT or not closed
        feed.append(
            {
                "kind": "support",
                "filter": "urgent" if urgent else "resolved",
                "title": ticket.subject,
                "subtitle": ticket.message,
                "contact": support_requester_label(ticket) or "Kontakt nije upisan",
                "status": ticket.get_status_display(),
                "created_at": ticket.created_at,
                "urgent": urgent,
            }
        )

    return sorted(feed, key=lambda item: item["created_at"], reverse=True)[:18]


def dashboard_conversation_messages(request, conv_id):
    """Return JSON message thread for inline conversation detail in the dashboard."""
    import json as _json
    from django.http import JsonResponse
    if not request.user.is_authenticated:
        return JsonResponse({"error": "auth"}, status=401)
    from communications.models import Message as Msg
    # Verify ownership
    try:
        conv = Conversation.objects.select_related("business_client", "customer").get(pk=conv_id)
    except Conversation.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    # Check access
    from clients.models import get_active_client_for_user
    if not request.user.is_staff and not request.user.is_superuser:
        accessible = get_active_client_for_user(request.user)
        if not accessible or accessible.id != conv.business_client_id:
            return JsonResponse({"error": "forbidden"}, status=403)
    msgs = list(
        Msg.objects.filter(conversation=conv)
        .order_by("created_at")
        .values("id", "direction", "body", "sender_label", "created_at", "message_type")
    )
    for m in msgs:
        m["created_at"] = m["created_at"].strftime("%d.%m. %H:%M")
    return JsonResponse({
        "conversation_id": conv.id,
        "channel": conv.channel,
        "status": conv.status,
        "customer": conv.customer.full_name if conv.customer else "",
        "messages": msgs,
    })


def build_billing_client_rows(clients):
    rows = []
    stats = {
        "active": 0,
        "trial": 0,
        "past_due": 0,
        "cancelled": 0,
        "none": 0,
        "needs_attention": 0,
    }
    now = timezone.now()

    for client in clients:
        subscription = get_client_subscription(client)
        status_code = subscription.status if subscription else "none"
        stats[status_code if status_code in stats else "none"] += 1
        badge_class = "ok"
        issue = "OK"
        action = "Nema akcije"
        needs_attention = False

        if not subscription:
            badge_class = "off"
            issue = "Nema pretplate"
            action = "Proveri da li je nalog rucno kreiran ili checkout nije zavrsen."
            needs_attention = True
        elif subscription.status == Subscription.STATUS_PAST_DUE:
            badge_class = "off"
            issue = "Naplata nije prosla"
            action = "Kontaktirati klijenta ili proveriti Lemon Squeezy event."
            needs_attention = True
        elif subscription.status == Subscription.STATUS_CANCELLED:
            badge_class = "off"
            issue = "Pretplata je otkazana"
            action = "Proveriti da li pristup treba da ostane ugasen."
            needs_attention = True
        elif subscription.status == Subscription.STATUS_TRIAL:
            badge_class = "pause"
            if subscription.trial_ends_at and subscription.trial_ends_at < now:
                issue = "Trial je istekao"
                action = "Proveriti da li je placanje aktiviralo pretplatu."
                needs_attention = True
            else:
                issue = "Trial aktivan"
                action = "Pratiti kraj trial perioda."

        if subscription and not client.kaleya_enabled and subscription.status in {
            Subscription.STATUS_ACTIVE,
            Subscription.STATUS_TRIAL,
        }:
            badge_class = "pause"
            issue = "Pristup je pauziran"
            action = "Aktiviraj klijenta ako je naplata uredna."
            needs_attention = True

        if needs_attention:
            stats["needs_attention"] += 1

        due_at = None
        if subscription:
            due_at = subscription.current_period_end or subscription.trial_ends_at

        rows.append(
            {
                "client": client,
                "subscription": subscription,
                "status_code": status_code,
                "status_label": subscription.get_status_display() if subscription else "Nema pretplate",
                "badge_class": badge_class,
                "access_label": "Aktivan" if client.kaleya_enabled else "Pauza",
                "access_badge_class": "ok" if client.kaleya_enabled else "pause",
                "due_at": due_at,
                "price": subscription.plan.monthly_price if subscription and subscription.plan else None,
                "currency": subscription.plan.currency if subscription and subscription.plan else "",
                "issue": issue,
                "action": action,
                "needs_attention": needs_attention,
            }
        )

    rows.sort(key=lambda item: (not item["needs_attention"], item["client"].name.lower()))
    return rows, stats


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
            is_owner = selected_client and selected_client.owner_id == request.user.id
            if not is_admin_user(request.user) and not is_owner:
                messages.error(request, "Samo vlasnik ili admin moze da menja radnike i usluge.")
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
        elif section == "telegram_integration":
            update_telegram_integration(request, selected_client)
            messages.success(request, "Telegram integracija je sacuvana.")
        elif section == "whatsapp_integration":
            update_whatsapp_integration(request, selected_client)
            messages.success(request, "WhatsApp integracija je sačuvana.")
        elif section == "viber_integration":
            update_viber_integration(request, selected_client)
            messages.success(request, "Viber integracija je sačuvana.")
        elif section == "instagram_integration":
            update_instagram_integration(request, selected_client)
            messages.success(request, "Instagram integracija je sačuvana.")
        elif section == "provision_phone" and is_admin_user(request.user):
            try:
                from communications.twilio_provision import provision_twilio_number, ProvisionError
                instructions = provision_twilio_number(selected_client)
                kaleya_num = instructions["kaleya_number"]
                messages.success(
                    request,
                    f"✅ Kaleya broj kupljen: {kaleya_num} ({instructions['country_name']}). "
                    f"Vlasnik treba da ukuca: {instructions['code_forward_all']} za preusmeravanje svih poziva.",
                )
            except Exception as exc:
                err = str(exc)
                if err.startswith("RU:"):
                    messages.warning(request, "🇷🇺 Rusija nije podržana automatski — kontaktirajte vlasnika da se javi Kaleya podršci.")
                else:
                    messages.error(request, f"Greška pri kupovini broja: {err}")
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#integrations")
        elif section == "release_phone" and is_admin_user(request.user):
            try:
                from communications.twilio_provision import release_twilio_number
                released = release_twilio_number(selected_client)
                if released:
                    messages.success(request, "Twilio broj je oslobođen.")
                else:
                    messages.warning(request, "Ovaj klijent nema dodeljen Twilio broj.")
            except Exception as exc:
                messages.error(request, f"Greška pri oslobađanju broja: {exc}")
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#integrations")
        elif section == "resend_setup_link" and is_admin_user(request.user):
            owner = selected_client.owner
            if owner:
                from billing.services import _send_setup_email
                _send_setup_email(owner, selected_client)
                messages.success(request, f"Setup email poslat na {owner.email}.")
            else:
                messages.error(request, "Klijent nema vlasnika — ne mogu da pošaljem email.")
            return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#clients")
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

        return redirect(f"{reverse('dashboard')}?client_id={selected_client.id}#{dashboard_section_anchor(section)}")

    integrations = ensure_integrations(selected_client)
    telegram_integration = next((item for item in integrations if item.provider == "telegram"), None)
    whatsapp_integration = next((item for item in integrations if item.provider == "whatsapp"), None)
    viber_integration = next((item for item in integrations if item.provider == "viber"), None)
    instagram_integration = next((item for item in integrations if item.provider == "instagram"), None)
    phone_integration = next((item for item in integrations if item.provider == "phone"), None)

    # ── Real-time statistics ────────────────────────────────────────────────
    _today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    _calls_today = CallSession.objects.filter(
        business_client=selected_client, started_at__gte=_today_start
    )
    stats_active_calls = _calls_today.filter(status="active").count()
    stats_missed_today = _calls_today.filter(status="missed").count()
    stats_transferred_today = _calls_today.filter(status="transferred").count()
    stats_total_calls_today = _calls_today.count()
    stats_total_conversations = Conversation.objects.filter(business_client=selected_client).count()

    # ── Calendar week view ──────────────────────────────────────────────────
    _today = timezone.localdate()
    _week_start = _today - timedelta(days=_today.weekday())  # Monday
    _week_end = _week_start + timedelta(days=6)
    _week_appts = (
        Appointment.objects.select_related("customer", "service", "staff_member")
        .filter(
            business_client=selected_client,
            date__range=[_week_start, _week_end],
            status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
        )
        .order_by("date", "start_time")
    )
    _days_sr = ["Pon", "Uto", "Sri", "Čet", "Pet", "Sub", "Ned"]
    calendar_week = []
    for i in range(7):
        _day = _week_start + timedelta(days=i)
        _day_appts = [a for a in _week_appts if a.date == _day]
        calendar_week.append({
            "date": _day,
            "label": _days_sr[i],
            "is_today": _day == _today,
            "appointments": _day_appts,
        })

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
    conversation_feed = build_conversation_feed(selected_client)
    admin_has_full_access = is_admin_user(request.user)
    payment_webhook_events = PaymentWebhookEvent.objects.none()
    payment_webhook_total = 0
    payment_webhook_processed = 0
    payment_webhook_failed = 0
    payment_webhook_pending = 0
    billing_client_rows = []
    billing_client_stats = {}
    if admin_has_full_access:
        payment_webhooks = PaymentWebhookEvent.objects.select_related("checkout", "checkout__plan")
        payment_webhook_events = payment_webhooks.order_by("-created_at")[:20]
        payment_webhook_total = payment_webhooks.count()
        payment_webhook_processed = payment_webhooks.filter(status=PaymentWebhookEvent.STATUS_PROCESSED).count()
        payment_webhook_failed = payment_webhooks.filter(status=PaymentWebhookEvent.STATUS_FAILED).count()
        payment_webhook_pending = payment_webhooks.filter(
            status__in=(PaymentWebhookEvent.STATUS_RECEIVED, PaymentWebhookEvent.STATUS_VERIFIED)
        ).count()
        billing_client_rows, billing_client_stats = build_billing_client_rows(clients)

    global_ai_provider = getattr(settings, "KALEYA_AI_PROVIDER", "") or "anthropic"
    global_ai_model = (
        getattr(settings, "KALEYA_ANTHROPIC_MODEL", "")
        or getattr(settings, "KALEYA_OPENAI_MODEL", "")
        or ""
    )
    global_voice_provider = "elevenlabs" if getattr(settings, "KALEYA_ELEVENLABS_API_KEY", "") else ""
    global_voice_model = "eleven_multilingual_v2" if global_voice_provider else ""
    global_voice_id = getattr(settings, "KALEYA_ELEVENLABS_VOICE_ID", "") or ""

    context = {
        "is_admin_user": admin_has_full_access,
        "is_owner": selected_client and selected_client.owner_id == request.user.id,
        "clients": clients,
        "selected_client": selected_client,
        "api_settings": api_settings,
        "alarm_settings": alarm_settings,
        "voice_settings": voice_settings,
        "integrations": integrations,
        "telegram_integration": telegram_integration,
        "whatsapp_integration": whatsapp_integration,
        "whatsapp_webhook_url": request.build_absolute_uri(reverse("whatsapp-incoming")),
        "viber_integration": viber_integration,
        "viber_webhook_url": request.build_absolute_uri(reverse("viber-webhook", args=[viber_integration.id])) if viber_integration else "",
        "instagram_integration": instagram_integration,
        "instagram_webhook_url": request.build_absolute_uri(reverse("whatsapp-webhook", args=[instagram_integration.id])) if instagram_integration else "",
        "phone_integration": phone_integration,
        "stats_active_calls": stats_active_calls,
        "stats_missed_today": stats_missed_today,
        "stats_transferred_today": stats_transferred_today,
        "stats_total_calls_today": stats_total_calls_today,
        "stats_total_conversations": stats_total_conversations,
        "calendar_week": calendar_week,
        "phone_kaleya_number": (phone_integration.public_number if phone_integration else "") or "",
        "phone_country": ((phone_integration.config or {}).get("country", "") if phone_integration else "") or "",
        "telegram_bot_token_configured": bool((telegram_integration.config or {}).get("bot_token")) if telegram_integration else False,
        "telegram_webhook_secret_configured": bool((telegram_integration.config or {}).get("webhook_secret")) if telegram_integration else False,
        "telegram_webhook_secret": (telegram_integration.config or {}).get("webhook_secret", "") if telegram_integration else "",
        "telegram_webhook_url": request.build_absolute_uri(reverse("telegram-webhook", args=[telegram_integration.id])) if telegram_integration else "",
        "selected_subscription": selected_subscription,
        "selected_staff_members": selected_staff_members,
        "selected_services": selected_services,
        "selected_working_hours": selected_working_hours,
        "selected_blocked_times": selected_blocked_times,
        "selected_ai_logs": selected_ai_logs,
        "selected_appointment_total": selected_appointment_total,
        "conversation_feed": conversation_feed,
        "upcoming_appointments": upcoming_appointments,
        "today_summary": today_summary,
        "cancelled_count": cancelled_count,
        "payment_webhook_events": payment_webhook_events,
        "payment_webhook_total": payment_webhook_total,
        "payment_webhook_processed": payment_webhook_processed,
        "payment_webhook_failed": payment_webhook_failed,
        "payment_webhook_pending": payment_webhook_pending,
        "billing_client_rows": billing_client_rows,
        "billing_client_stats": billing_client_stats,
        "language_choices": BusinessClient.LANGUAGE_CHOICES,
        "package_choices": BusinessClient.PACKAGE_CHOICES,
        "time_format_choices": BusinessClient.TIME_FORMAT_CHOICES,
        "date_format_choices": BusinessClient.DATE_FORMAT_CHOICES,
        "week_start_choices": BusinessClient.WEEK_START_CHOICES,
        "slot_choices": [15, 20, 30, 45, 60],
        "global_ai_provider": global_ai_provider,
        "global_ai_model": global_ai_model,
        "global_ai_key_configured": bool(getattr(settings, "KALEYA_ANTHROPIC_API_KEY", "") or getattr(settings, "KALEYA_OPENAI_API_KEY", "")),
        "global_voice_provider": global_voice_provider,
        "global_voice_model": global_voice_model,
        "global_voice_id": global_voice_id,
        "global_voice_key_configured": bool(getattr(settings, "KALEYA_ELEVENLABS_API_KEY", "")),
        # Onboarding
        "show_welcome": request.GET.get("welcome") == "1",
        "onboarding_has_staff": selected_staff_members.exists(),
        "onboarding_has_services": selected_services.exists(),
        "onboarding_has_phone": bool((phone_integration.public_number if phone_integration else "")),
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
    # Only admins can change the billing package to prevent self-upgrades
    if is_admin_user(request.user):
        client.package = post.get("package", client.package)
    client.business_phone = post.get("business_phone", client.business_phone).strip()
    client.business_email = post.get("business_email", client.business_email).strip()
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
    api_settings.master_prompt = post.get("master_prompt", api_settings.master_prompt).strip()

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


def update_telegram_integration(request, client):
    integration, _created = IntegrationConnection.objects.get_or_create(
        business_client=client,
        provider="telegram",
        defaults={"enabled": False, "status": "draft"},
    )
    config = dict(integration.config or {})

    bot_token = request.POST.get("telegram_bot_token", "").strip()
    webhook_secret = request.POST.get("telegram_webhook_secret", "").strip()
    if bot_token:
        config["bot_token"] = bot_token
    if webhook_secret:
        config["webhook_secret"] = webhook_secret
    elif not config.get("webhook_secret"):
        config["webhook_secret"] = secrets.token_urlsafe(32)

    integration.enabled = checkbox_value(request.POST, "telegram_enabled")
    integration.status = request.POST.get("telegram_status", integration.status)
    integration.public_number = request.POST.get("telegram_public_number", integration.public_number).strip()
    integration.webhook_url = request.POST.get("telegram_webhook_url", integration.webhook_url).strip()
    integration.config = config
    if integration.status != "error":
        integration.last_error = ""
    integration.full_clean()
    integration.save()

    # Auto-register Telegram webhook when bot_token is provided and integration is enabled
    if config.get("bot_token") and integration.enabled:
        from django.urls import reverse as _reverse
        from integrations.services import configure_telegram_webhook, telegram_api_post
        webhook_url = request.build_absolute_uri(
            _reverse("telegram-webhook", args=[integration.id])
        )
        try:
            configure_telegram_webhook(integration, webhook_url)
            # Try to fetch bot username to display it
            bot_info = telegram_api_post(integration, "getMe", {})
            if bot_info.get("ok") and bot_info.get("result"):
                username = bot_info["result"].get("username", "")
                if username:
                    integration.public_number = f"@{username}"
                    integration.save(update_fields=["public_number", "updated_at"])
        except Exception as exc:
            integration.status = "error"
            integration.last_error = str(exc)
            integration.save(update_fields=["status", "last_error", "updated_at"])


def update_whatsapp_integration(request, client):
    integration, _created = IntegrationConnection.objects.get_or_create(
        business_client=client,
        provider="whatsapp",
        defaults={"enabled": False, "status": "draft"},
    )
    # Strip whatsapp: prefix if the user pasted the full Twilio format
    public_number = request.POST.get("whatsapp_public_number", integration.public_number).strip()
    public_number = public_number.replace("whatsapp:", "").strip()

    integration.enabled = checkbox_value(request.POST, "whatsapp_enabled")
    integration.status = request.POST.get("whatsapp_status", integration.status)
    integration.public_number = public_number
    if integration.status != "error":
        integration.last_error = ""
    integration.save()


def update_viber_integration(request, client):
    integration, _created = IntegrationConnection.objects.get_or_create(
        business_client=client,
        provider="viber",
        defaults={"enabled": False, "status": "draft"},
    )
    config = dict(integration.config or {})
    auth_token = request.POST.get("viber_auth_token", "").strip()
    sender_name = request.POST.get("viber_sender_name", "").strip()
    if auth_token:
        config["auth_token"] = auth_token
    if sender_name:
        config["sender_name"] = sender_name

    integration.enabled = checkbox_value(request.POST, "viber_enabled")
    integration.status = request.POST.get("viber_status", integration.status)
    integration.config = config
    if integration.status != "error":
        integration.last_error = ""
    integration.save()

    # Auto-register Viber webhook if auth_token is now set
    if config.get("auth_token") and integration.enabled:
        from django.urls import reverse as _reverse
        from integrations.services import configure_viber_webhook
        webhook_url = request.build_absolute_uri(
            _reverse("viber-webhook", args=[integration.id])
        )
        try:
            configure_viber_webhook(integration, webhook_url)
        except Exception as exc:
            integration.status = "error"
            integration.last_error = str(exc)
            integration.save(update_fields=["status", "last_error", "updated_at"])


def update_instagram_integration(request, client):
    integration, _created = IntegrationConnection.objects.get_or_create(
        business_client=client,
        provider="instagram",
        defaults={"enabled": False, "status": "draft"},
    )
    config = dict(integration.config or {})
    access_token = request.POST.get("instagram_access_token", "").strip()
    business_account_id = request.POST.get("instagram_business_account_id", "").strip()
    verify_token = request.POST.get("instagram_verify_token", "").strip()
    if access_token:
        config["access_token"] = access_token
    if business_account_id:
        config["business_account_id"] = business_account_id
    if verify_token:
        config["verify_token"] = verify_token

    integration.enabled = checkbox_value(request.POST, "instagram_enabled")
    integration.status = request.POST.get("instagram_status", integration.status)
    integration.config = config
    if integration.status != "error":
        integration.last_error = ""
    integration.save()


# ─────────────────────────────────────────────────────────────────────────────
# Account setup (password set after payment — one-time token link)
# ─────────────────────────────────────────────────────────────────────────────

_PASSWORD_RE = re.compile(
    r'^(?=.*[A-Z])'    # at least one uppercase
    r'(?=.*[a-z])'    # at least one lowercase
    r'(?=.*\d)'       # at least one digit
    r'(?=.*[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?\\|`~])'  # special char
    r'[^\s]{8,}$'     # min 8 chars, no spaces
)


def setup_account(request):
    """
    GET  /setup/?token=<token>  — show password-setup form
    POST /setup/?token=<token>  — validate + set password, auto-login, redirect dashboard
    """
    from accounts.models import AccountSetupToken

    token_value = request.GET.get("token", "").strip() or request.POST.get("token", "").strip()
    error = None
    token_obj = None

    if token_value:
        token_obj = AccountSetupToken.objects.select_related("user").filter(token=token_value).first()

    if not token_value or not token_obj:
        return render(request, "setup.html", {"state": "invalid", "error": "Invalid or missing setup link."})

    if not token_obj.is_valid:
        return render(request, "setup.html", {"state": "expired", "error": "This setup link has expired. Please contact support."})

    if request.method == "POST":
        password  = request.POST.get("password", "")
        password2 = request.POST.get("password2", "")

        if not password:
            error = "Please enter a password."
        elif password != password2:
            error = "Passwords do not match."
        elif not _PASSWORD_RE.match(password):
            error = (
                "Password must be at least 8 characters and contain "
                "an uppercase letter, a lowercase letter, a number, "
                "and a special character (!@#$%^&* etc.). No spaces allowed."
            )
        else:
            user = token_obj.user
            user.set_password(password)
            user.save(update_fields=["password"])
            token_obj.mark_used()

            # Auto-login and send to dashboard
            user.backend = "django.contrib.auth.backends.ModelBackend"
            auth_login(request, user)
            return redirect("/dashboard/?welcome=1")

    return render(request, "setup.html", {
        "state": "form",
        "token": token_value,
        "error": error,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Forgot password — resend setup link by email
# ─────────────────────────────────────────────────────────────────────────────

def forgot_password(request):
    """
    GET  /forgot-password/  — show email form
    POST /forgot-password/  — look up user, send setup link, always show success
    """
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if email:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=email)
                # Only send if this user owns a business client
                bc = BusinessClient.objects.filter(owner=user).first()
                if bc:
                    from billing.services import _send_setup_email
                    _send_setup_email(user, bc)
            except User.DoesNotExist:
                pass  # Silently ignore — don't reveal whether email exists
        # Always show "check your inbox" — no info leakage
        return render(request, "forgot_password.html", {"sent": True})

    return render(request, "forgot_password.html", {"sent": False})
