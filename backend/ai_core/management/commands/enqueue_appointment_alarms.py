"""Enqueue dashboard alarms for appointments that start in ~5 minutes.

Usage: python manage.py enqueue_appointment_alarms

Recommended cron schedule: every minute.
  * * * * * cd /var/www/aikaleya && .venv/bin/python backend/manage.py enqueue_appointment_alarms >> /var/log/kaleya_alarms.log 2>&1

Logic:
  - Look at appointments starting within the next [LEAD_MIN, LEAD_MIN + WINDOW] minutes
  - Skip ones that already have a non-dismissed next_in_line AlarmEvent
  - Create one AlarmEvent per matching appointment + tenant
  - Optional: also dispatch via WhatsApp / SMS if the tenant's plan allows
    AND the assigned staff member has a phone on file
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_core.models import AlarmEvent, AlarmSettings
from appointments.models import Appointment
from billing.services import limits_for_client


# How many minutes before the appointment we fire the "next in line" alarm
LEAD_MIN = 5
# Half-window — cron runs every minute, this prevents missing one if cron is late
WINDOW_MIN = 2


def _speak_text(appointment, lang: str) -> str:
    customer = appointment.customer
    first_name = (getattr(customer, "first_name", "") or "").strip()
    if not first_name and customer:
        first_name = (getattr(customer, "full_name", "") or "").split(" ")[0]
    first_name = first_name or "Next client"

    service = appointment.service.name if appointment.service else ""
    time_str = appointment.start_time.strftime("%I:%M %p").lstrip("0")

    templates = {
        "en": f"{first_name} is next in line, scheduled at {time_str}" + (f" for {service}." if service else "."),
        "es": f"{first_name} es el siguiente en la fila, a las {time_str}" + (f" para {service}." if service else "."),
        "pt": f"{first_name} é o próximo da fila, às {time_str}" + (f" para {service}." if service else "."),
        "fr": f"{first_name} est le prochain, à {time_str}" + (f" pour {service}." if service else "."),
        "it": f"{first_name} è il prossimo, alle {time_str}" + (f" per {service}." if service else "."),
        "de": f"{first_name} ist als Nächster dran, um {time_str}" + (f" für {service}." if service else "."),
        "ru": f"{first_name} следующий в очереди, в {time_str}" + (f" — {service}." if service else "."),
        "sr": f"{first_name} je sledeći na redu, u {time_str}" + (f" za {service}." if service else "."),
    }
    return templates.get(lang, templates["en"])


def _title(appointment, lang: str) -> str:
    customer = appointment.customer
    name = ""
    if customer:
        name = (getattr(customer, "full_name", "") or getattr(customer, "first_name", "") or "").strip()
    name = name or "Next client"
    time_str = appointment.start_time.strftime("%H:%M")
    if lang in ("sr", "hr", "bs"):
        return f"{name} — sledeći u redu ({time_str})"
    return f"{name} — next in line ({time_str})"


def _dispatch_external(business_client, alarm, appointment):
    """Optional WhatsApp/SMS dispatch to staff phone if plan allows."""
    if not appointment.staff_member or not appointment.staff_member.phone:
        return

    settings_obj = getattr(business_client, "alarm_settings", None)
    if not settings_obj or not settings_obj.notifications_enabled:
        return

    limits = limits_for_client(business_client)
    target_phone = appointment.staff_member.phone
    channels = list(alarm.channels or [])

    # WhatsApp dispatch (preferred, cheaper) — Pro+ only
    if limits and limits.allow_whatsapp:
        try:
            from integrations.services import send_whatsapp_message
            from integrations.models import IntegrationConnection
            wa_conn = (
                IntegrationConnection.objects
                .filter(business_client=business_client, provider="whatsapp", enabled=True)
                .first()
            )
            if wa_conn:
                send_whatsapp_message(wa_conn, target_phone, alarm.body or alarm.title)
                channels.append("whatsapp")
        except Exception:
            pass

    # SMS dispatch — Pro+ only
    elif limits and limits.allow_sms:
        try:
            from communications.twilio_service import send_sms
            result = send_sms(business_client, target_phone, alarm.body or alarm.title)
            if not result.get("error"):
                channels.append("sms")
        except Exception:
            pass

    if channels != (alarm.channels or []):
        alarm.channels = channels
        alarm.save(update_fields=["channels"])


class Command(BaseCommand):
    help = "Enqueue dashboard alarms for appointments starting in ~5 minutes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--lead-minutes", type=int, default=LEAD_MIN,
            help=f"Minutes before appointment start to fire (default {LEAD_MIN})",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be enqueued without writing.",
        )

    def handle(self, *args, **opts):
        lead = opts["lead_minutes"]
        dry = opts["dry_run"]
        now = timezone.now()

        # Window: appointments starting between [now + lead - WINDOW, now + lead + WINDOW]
        lo = now + timedelta(minutes=lead - WINDOW_MIN)
        hi = now + timedelta(minutes=lead + WINDOW_MIN)

        # Pre-filter by today's date to keep the query cheap
        # (we'll evaluate exact datetime in Python because Appointment uses date+start_time)
        upcoming = Appointment.objects.filter(
            status__in=(Appointment.STATUS_CONFIRMED, Appointment.STATUS_PENDING),
            date=now.date(),
        ).select_related("business_client", "customer", "service", "staff_member")

        created = 0
        skipped = 0

        for appt in upcoming:
            try:
                appt_dt = datetime.combine(appt.date, appt.start_time)
            except Exception:
                continue
            if timezone.is_naive(appt_dt):
                appt_dt = timezone.make_aware(appt_dt, timezone.get_current_timezone())

            if not (lo <= appt_dt <= hi):
                continue

            # Already have a live next_in_line alarm for this appointment?
            already = AlarmEvent.objects.filter(
                appointment=appt,
                kind=AlarmEvent.KIND_NEXT_IN_LINE,
                dismissed_at__isnull=True,
            ).exists()
            if already:
                skipped += 1
                continue

            lang = (
                appt.business_client.interface_language
                or appt.business_client.language
                or "en"
            )
            speak = _speak_text(appt, lang)
            title = _title(appt, lang)

            if dry:
                self.stdout.write(f"[DRY] {appt.business_client} | {title} | TTS: {speak}")
                continue

            alarm = AlarmEvent.objects.create(
                business_client=appt.business_client,
                kind=AlarmEvent.KIND_NEXT_IN_LINE,
                title=title,
                body=speak,
                speak_text=speak,
                speak_lang=lang,
                appointment=appt,
                target_staff=appt.staff_member,
                channels=[],
                metadata={"lead_minutes": lead},
            )
            created += 1
            self.stdout.write(f"Queued: {title} for {appt.business_client}")

            # Optional WhatsApp/SMS dispatch (gated by plan + staff phone)
            _dispatch_external(appt.business_client, alarm, appt)

        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, skipped (already queued): {skipped}"
        ))
