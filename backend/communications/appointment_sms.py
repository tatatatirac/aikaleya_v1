"""Send SMS notifications when appointments are created or move forward.

Wired via Django signals — every Appointment.save() that produces a new
confirmed/pending booking triggers a confirmation SMS to the customer.
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from appointments.models import Appointment
from communications.twilio_service import send_sms


logger = logging.getLogger(__name__)


def localized_confirmation_text(business_client, appointment) -> str:
    lang = business_client.interface_language or business_client.language or "en"
    shop = (business_client.public_name or business_client.name or "").strip() or "the shop"
    service = appointment.service.name if appointment.service else "your appointment"
    date_str = appointment.date.strftime("%a %b %d")
    time_str = appointment.start_time.strftime("%I:%M %p")

    templates = {
        "en":    f"Hi! Your {service} is booked at {shop} for {date_str} at {time_str}. Reply C to confirm or R to reschedule.",
        "en-gb": f"Hi! Your {service} is booked at {shop} for {date_str} at {time_str}. Reply C to confirm or R to reschedule.",
        "es":    f"¡Hola! Tu cita de {service} en {shop} está reservada para {date_str} a las {time_str}. Responde C para confirmar o R para cambiar.",
        "pt":    f"Olá! O teu {service} no {shop} está marcado para {date_str} às {time_str}. Responde C para confirmar ou R para remarcar.",
        "fr":    f"Bonjour ! Votre {service} chez {shop} est prévu le {date_str} à {time_str}. Répondez C pour confirmer ou R pour reporter.",
        "it":    f"Ciao! Il tuo {service} da {shop} è prenotato per {date_str} alle {time_str}. Rispondi C per confermare o R per spostare.",
        "de":    f"Hallo! Dein {service} bei {shop} ist für {date_str} um {time_str} gebucht. Antworte C zum Bestätigen oder R zum Verschieben.",
        "ru":    f"Привет! Ваша запись «{service}» в {shop} забронирована на {date_str} в {time_str}. Ответьте C для подтверждения или R для переноса.",
        "sr":    f"Zdravo! Termin za {service} u {shop} je zakazan za {date_str} u {time_str}. Odgovorite C za potvrdu ili R za promenu.",
    }
    return templates.get(lang) or templates["en"]


@receiver(post_save, sender=Appointment)
def send_appointment_confirmation_sms(sender, instance, created, **kwargs):
    """Fire a confirmation SMS once per appointment.

    Conditions:
      - newly created OR transitioning into confirmed/pending status
      - customer has a phone number
      - we haven't already sent confirmation (idempotency flag in metadata)
    """
    if instance.status not in {Appointment.STATUS_CONFIRMED, Appointment.STATUS_PENDING}:
        return
    if not instance.customer or not instance.customer.phone:
        return

    metadata = dict(instance.metadata or {})
    if metadata.get("sms_confirmation_sent"):
        return

    text = localized_confirmation_text(instance.business_client, instance)
    result = send_sms(instance.business_client, instance.customer.phone, text)

    if result.get("error"):
        logger.warning("Appointment SMS failed: %s", result["error"])
        return

    metadata["sms_confirmation_sent"] = True
    metadata["sms_confirmation_sid"] = result.get("sid", "")
    # Use update to avoid recursive signal trigger
    Appointment.objects.filter(pk=instance.pk).update(metadata=metadata)
