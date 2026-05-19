"""Send 24h and 2h reminder SMS for upcoming appointments.

Usage: python manage.py send_appointment_reminders

Recommended cron schedule: every 15 minutes.
  */15 * * * * cd /var/www/aikaleya && .venv/bin/python backend/manage.py send_appointment_reminders >> /var/log/kaleya_reminders.log 2>&1
"""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from appointments.models import Appointment
from communications.twilio_service import send_sms


REMINDER_24H_KEY = "sms_reminder_24h_sent"
REMINDER_2H_KEY = "sms_reminder_2h_sent"

# Half-window around the target offset so cron firing every 15 min always catches it
WINDOW_MINUTES = 15


def reminder_text(business_client, appointment, *, hours_ahead: int) -> str:
    lang = business_client.interface_language or business_client.language or "en"
    shop = (business_client.public_name or business_client.name or "").strip() or "the shop"
    service = appointment.service.name if appointment.service else "your appointment"
    time_str = appointment.start_time.strftime("%I:%M %p")
    date_str = appointment.date.strftime("%a %b %d")

    if hours_ahead == 2:
        templates = {
            "en":    f"Heads up — your {service} at {shop} is in 2 hours ({time_str}). See you soon!",
            "es":    f"Recordatorio — tu {service} en {shop} es en 2 horas ({time_str}). ¡Nos vemos pronto!",
            "pt":    f"Lembrete — o teu {service} no {shop} é em 2 horas ({time_str}). Até já!",
            "fr":    f"Rappel — votre {service} chez {shop} est dans 2 heures ({time_str}). À tout à l'heure !",
            "it":    f"Promemoria — il tuo {service} da {shop} è tra 2 ore ({time_str}). A presto!",
            "de":    f"Erinnerung — dein {service} bei {shop} ist in 2 Stunden ({time_str}). Bis gleich!",
            "ru":    f"Напоминание — ваша запись «{service}» в {shop} через 2 часа ({time_str}).",
            "sr":    f"Podsetnik — vaš {service} u {shop} je za 2 sata ({time_str}). Vidimo se uskoro!",
        }
    else:
        templates = {
            "en":    f"Reminder: {service} at {shop} tomorrow {date_str} at {time_str}. Reply C to confirm or R to reschedule.",
            "es":    f"Recordatorio: {service} en {shop} mañana {date_str} a las {time_str}. C para confirmar o R para cambiar.",
            "pt":    f"Lembrete: {service} no {shop} amanhã {date_str} às {time_str}. C para confirmar ou R para remarcar.",
            "fr":    f"Rappel : {service} chez {shop} demain {date_str} à {time_str}. C pour confirmer, R pour reporter.",
            "it":    f"Promemoria: {service} da {shop} domani {date_str} alle {time_str}. C per confermare, R per spostare.",
            "de":    f"Erinnerung: {service} bei {shop} morgen {date_str} um {time_str}. C bestätigen, R verschieben.",
            "ru":    f"Напоминание: {service} в {shop} завтра {date_str} в {time_str}. C — подтвердить, R — перенести.",
            "sr":    f"Podsetnik: {service} u {shop} sutra {date_str} u {time_str}. C za potvrdu ili R za promenu.",
        }
    return templates.get(lang) or templates["en"]


class Command(BaseCommand):
    help = "Send 24h and 2h SMS reminders for upcoming appointments."

    def handle(self, *args, **opts):
        now = timezone.now()
        sent_24, sent_2 = 0, 0
        skipped = 0

        upcoming = Appointment.objects.filter(
            status__in=[Appointment.STATUS_CONFIRMED, Appointment.STATUS_PENDING],
            date__gte=now.date(),
        ).select_related("business_client", "customer", "service")

        for appt in upcoming:
            if not appt.customer or not appt.customer.phone:
                skipped += 1
                continue

            # Build a naive datetime for the appointment start; assume the
            # business_client.timezone matches server timezone for simplicity.
            try:
                appt_dt = datetime.combine(appt.date, appt.start_time)
            except Exception:
                skipped += 1
                continue
            appt_dt = timezone.make_aware(appt_dt, timezone.get_current_timezone()) if timezone.is_naive(appt_dt) else appt_dt

            minutes_to_go = (appt_dt - now).total_seconds() / 60.0
            metadata = dict(appt.metadata or {})

            # 24-hour reminder: between 24h-WINDOW and 24h+WINDOW
            if (24 * 60 - WINDOW_MINUTES) <= minutes_to_go <= (24 * 60 + WINDOW_MINUTES):
                if not metadata.get(REMINDER_24H_KEY):
                    text = reminder_text(appt.business_client, appt, hours_ahead=24)
                    result = send_sms(appt.business_client, appt.customer.phone, text)
                    if not result.get("error"):
                        metadata[REMINDER_24H_KEY] = now.isoformat()
                        Appointment.objects.filter(pk=appt.pk).update(metadata=metadata)
                        sent_24 += 1
                        self.stdout.write(f"24h reminder → {appt.customer.phone} (appt {appt.pk})")
                    else:
                        self.stderr.write(f"24h reminder FAILED for appt {appt.pk}: {result['error']}")

            # 2-hour reminder
            elif (2 * 60 - WINDOW_MINUTES) <= minutes_to_go <= (2 * 60 + WINDOW_MINUTES):
                if not metadata.get(REMINDER_2H_KEY):
                    text = reminder_text(appt.business_client, appt, hours_ahead=2)
                    result = send_sms(appt.business_client, appt.customer.phone, text)
                    if not result.get("error"):
                        metadata[REMINDER_2H_KEY] = now.isoformat()
                        Appointment.objects.filter(pk=appt.pk).update(metadata=metadata)
                        sent_2 += 1
                        self.stdout.write(f"2h reminder → {appt.customer.phone} (appt {appt.pk})")
                    else:
                        self.stderr.write(f"2h reminder FAILED for appt {appt.pk}: {result['error']}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. 24h: {sent_24}, 2h: {sent_2}, skipped: {skipped}"
        ))
