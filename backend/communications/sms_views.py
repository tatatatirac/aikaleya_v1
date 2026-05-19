"""Twilio SMS webhook handlers.

Inbound flow:
  Twilio receives SMS to our number → POSTs to /api/communications/sms/incoming/
  We look up tenant (by To) and customer (by From), handle reserved replies
  (C = confirm, R = reschedule, STOP = opt-out) or hand off to AI for free text.
"""

import logging
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_agent.services import handle_inbound_text
from appointments.models import Appointment, Customer
from communications.models import Conversation, Message
from communications.twilio_service import find_business_client_by_called_number, send_sms


logger = logging.getLogger(__name__)


CONFIRM_KEYWORDS = {"c", "confirm", "yes", "y", "ok", "da", "ja", "si", "sí", "oui"}
RESCHEDULE_KEYWORDS = {"r", "reschedule", "change", "promeni", "cambiar", "ändern"}
OPT_OUT_KEYWORDS = {"stop", "unsubscribe", "end", "cancel", "stopall"}


def _twiml(xml: str) -> HttpResponse:
    return HttpResponse(xml, content_type="application/xml")


def _empty_response() -> HttpResponse:
    return _twiml('<?xml version="1.0" encoding="UTF-8"?><Response></Response>')


def _reply_response(text: str) -> HttpResponse:
    from xml.sax.saxutils import escape
    return _twiml(
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(text)}</Message></Response>"
    )


def _find_customer(business_client, phone_number: str):
    if not phone_number:
        return None
    cleaned = phone_number.strip()
    return (
        Customer.objects.filter(business_client=business_client, phone=cleaned).first()
        or Customer.objects.filter(business_client=business_client, phone__endswith=cleaned[-9:]).first()
    )


def _latest_pending_appointment(business_client, customer):
    if not customer:
        return None
    now = timezone.now()
    window_start = now.date()
    return (
        Appointment.objects.filter(
            business_client=business_client,
            customer=customer,
            status__in=[Appointment.STATUS_PENDING, Appointment.STATUS_CONFIRMED],
            date__gte=window_start,
        )
        .order_by("date", "start_time")
        .first()
    )


@csrf_exempt
@require_POST
def sms_incoming(request):
    from_number = request.POST.get("From", "").strip()
    to_number = request.POST.get("To", "").strip()
    body = (request.POST.get("Body") or "").strip()
    message_sid = request.POST.get("MessageSid", "")

    business_client = find_business_client_by_called_number(to_number)
    if not business_client:
        logger.warning("Inbound SMS to %s — no matching tenant.", to_number)
        return _empty_response()

    customer = _find_customer(business_client, from_number)

    # Persist the inbound message regardless of resolution
    conversation, _ = Conversation.objects.get_or_create(
        business_client=business_client,
        channel="sms",
        external_thread_id=from_number,
        defaults={"customer": customer, "language": business_client.interface_language or "en"},
    )
    if customer and not conversation.customer:
        conversation.customer = customer
        conversation.save(update_fields=["customer"])

    Message.objects.create(
        conversation=conversation,
        direction="inbound",
        message_type="text",
        sender_label=from_number,
        body=body,
        provider_message_id=message_sid,
        raw_payload=dict(request.POST.items()),
    )

    normalized = body.lower().strip()

    # Reserved keywords
    if normalized in OPT_OUT_KEYWORDS:
        return _reply_response(
            "You're unsubscribed. Reply START to opt back in."
        )

    if normalized in CONFIRM_KEYWORDS:
        appt = _latest_pending_appointment(business_client, customer)
        if appt:
            appt.status = Appointment.STATUS_CONFIRMED
            md = dict(appt.metadata or {})
            md["sms_confirmed_at"] = timezone.now().isoformat()
            appt.metadata = md
            appt.save(update_fields=["status", "metadata", "updated_at"])
            return _reply_response(
                f"Confirmed! See you {appt.date.strftime('%a %b %d')} at {appt.start_time.strftime('%I:%M %p')}."
            )
        return _reply_response("Thanks! We don't see an upcoming appointment to confirm. Reply with details or call us.")

    if normalized in RESCHEDULE_KEYWORDS:
        appt = _latest_pending_appointment(business_client, customer)
        if appt:
            md = dict(appt.metadata or {})
            md["sms_reschedule_requested_at"] = timezone.now().isoformat()
            appt.metadata = md
            appt.save(update_fields=["metadata", "updated_at"])
            return _reply_response(
                f"Got it. What day/time works better? We'll find a new slot for {appt.service.name if appt.service else 'your appointment'}."
            )
        return _reply_response("Reply with a day and time you'd prefer, e.g. 'Friday 4pm'.")

    # Free-form text — let the AI agent handle it
    try:
        result = handle_inbound_text(
            business_client,
            body,
            conversation=conversation,
            customer=customer,
            channel="sms",
            payload={"from_number": from_number},
            include_voice=False,
            external_thread_id=from_number,
            record_messages=False,  # we already saved the inbound above
        )
        response_text = (result.get("response_text") or "").strip()
    except Exception as exc:
        logger.warning("AI agent failed during SMS: %s", exc)
        response_text = "Thanks — we got your message. Someone will be in touch shortly."

    if not response_text:
        response_text = "Thanks — we got your message."

    # Record outbound and reply via TwiML (Twilio sends the SMS for us)
    Message.objects.create(
        conversation=conversation,
        direction="outbound",
        message_type="text",
        sender_label="Kaleya",
        body=response_text,
    )
    return _reply_response(response_text)
