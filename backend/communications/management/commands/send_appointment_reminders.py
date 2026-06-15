"""Send appointment reminders through the same channel the customer used
(Telegram for bot bookings, SMS when we have a phone), at each appointment's
own reminder offset (what Kaleya promised — default 60 min, or e.g. 30).

Usage: python manage.py send_appointment_reminders
Recommended cron (every ~5–10 min so the offset window is always caught):
  */5 * * * * cd /var/www/aikaleya && .venv/bin/python backend/manage.py send_appointment_reminders >> /var/log/kaleya_reminders.log 2>&1
"""

from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from appointments.services import client_timezone
from communications.twilio_service import send_sms
from integrations.models import IntegrationConnection
from integrations.services import send_telegram_message


REMINDER_SENT_KEY = "reminder_sent"
DEFAULT_OFFSET_MINUTES = 60
# Half-window around the target offset; with a 5–10 min cron this always fires once.
WINDOW_MINUTES = 8


def reminder_text(business_client, appointment) -> str:
    lang = business_client.interface_language or business_client.language or "en"
    shop = (business_client.public_name or business_client.name or "").strip() or "the shop"
    service = appointment.service.name if appointment.service else ("termin" if lang == "sr" else "your appointment")
    time_str = appointment.start_time.strftime("%H:%M")
    templates = {
        "en": f"Reminder: {service} at {shop} today at {time_str}. See you soon!",
        "es": f"Recordatorio: {service} en {shop} hoy a las {time_str}. ¡Nos vemos!",
        "pt": f"Lembrete: {service} no {shop} hoje às {time_str}. Até já!",
        "fr": f"Rappel : {service} chez {shop} aujourd'hui à {time_str}. À tout à l'heure !",
        "it": f"Promemoria: {service} da {shop} oggi alle {time_str}. A presto!",
        "de": f"Erinnerung: {service} bei {shop} heute um {time_str}. Bis gleich!",
        "ru": f"Напоминание: {service} в {shop} сегодня в {time_str}.",
        "sr": f"Podsetnik: {service} u {shop} danas u {time_str}. Vidimo se!",
    }
    return templates.get(lang) or templates["en"]


class Command(BaseCommand):
    help = "Send appointment reminders via Telegram or SMS at each appointment's reminder offset."

    def handle(self, *args, **opts):
        now = timezone.now()
        sent = 0
        skipped = 0

        upcoming = Appointment.objects.filter(
            status__in=[Appointment.STATUS_CONFIRMED, Appointment.STATUS_PENDING],
            date__gte=now.date(),
        ).select_related("business_client", "customer", "service")

        for appt in upcoming:
            metadata = dict(appt.metadata or {})
            if metadata.get(REMINDER_SENT_KEY):
                continue

            business_client = appt.business_client
            try:
                appt_dt = timezone.make_aware(
                    datetime.combine(appt.date, appt.start_time), client_timezone(business_client)
                )
            except Exception:
                skipped += 1
                continue

            try:
                offset = int(metadata.get("reminder_minutes_before", DEFAULT_OFFSET_MINUTES) or DEFAULT_OFFSET_MINUTES)
            except (TypeError, ValueError):
                offset = DEFAULT_OFFSET_MINUTES

            minutes_to_go = (appt_dt - now).total_seconds() / 60.0
            if not ((offset - WINDOW_MINUTES) <= minutes_to_go <= (offset + WINDOW_MINUTES)):
                continue

            text = reminder_text(business_client, appt)
            delivered = False

            # 1) Same channel the booking came through (Telegram for bot bookings).
            chat_id = metadata.get("telegram_chat_id")
            if chat_id:
                connection = IntegrationConnection.objects.filter(
                    business_client=business_client, provider="telegram", enabled=True
                ).first()
                if connection:
                    try:
                        send_telegram_message(connection, chat_id, text)
                        delivered = True
                    except Exception as exc:
                        self.stderr.write(f"Telegram reminder FAILED for appt {appt.pk}: {exc}")

            # 2) Fallback to SMS if we have a phone.
            if not delivered and appt.customer and appt.customer.phone:
                result = send_sms(business_client, appt.customer.phone, text)
                delivered = not result.get("error")
                if not delivered:
                    self.stderr.write(f"SMS reminder FAILED for appt {appt.pk}: {result.get('error')}")

            if delivered:
                metadata[REMINDER_SENT_KEY] = now.isoformat()
                Appointment.objects.filter(pk=appt.pk).update(metadata=metadata)
                sent += 1
                self.stdout.write(f"Reminder → appt {appt.pk} ({offset} min before)")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Sent: {sent}, skipped: {skipped}"))
