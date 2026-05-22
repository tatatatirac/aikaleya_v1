"""Twilio WhatsApp webhook handler.

Flow:
  Owner's WhatsApp customer → Twilio WhatsApp number → POST /api/communications/whatsapp/incoming/
  We look up tenant by To-number, run AI agent, reply via TwiML <Message>.

Twilio sends WhatsApp messages with "whatsapp:" prefix in From/To, e.g.:
  From=whatsapp:+381631234567
  To=whatsapp:+14155238886
"""

import logging
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_agent.services import handle_inbound_text
from appointments.models import Customer
from communications.models import Conversation, Message
from integrations.models import IntegrationConnection


logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _strip_prefix(number: str) -> str:
    """Remove 'whatsapp:' prefix Twilio adds to WhatsApp numbers."""
    return (number or "").replace("whatsapp:", "").strip()


def _twiml_msg(text: str) -> HttpResponse:
    return HttpResponse(
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f"<Response><Message>{escape(text)}</Message></Response>",
        content_type="application/xml",
    )


def _empty_response() -> HttpResponse:
    return HttpResponse(
        '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        content_type="application/xml",
    )


def _find_business_client(to_number: str):
    """Look up tenant by their Twilio WhatsApp number (stored without 'whatsapp:' prefix)."""
    from clients.models import BusinessClient

    # Try exact match first, then with prefix stripped
    for candidate in (to_number, _strip_prefix(to_number)):
        conn = (
            IntegrationConnection.objects
            .select_related("business_client")
            .filter(provider="whatsapp", public_number=candidate, enabled=True)
            .first()
        )
        if conn and conn.business_client:
            return conn.business_client

    # Dev fallback — first client in DB
    return BusinessClient.objects.first()


def _find_or_stub_customer(business_client, phone: str):
    if not phone:
        return None
    cleaned = phone.strip()
    return (
        Customer.objects.filter(business_client=business_client, phone=cleaned).first()
        or Customer.objects.filter(business_client=business_client, phone__endswith=cleaned[-9:]).first()
    )


# ── webhook ───────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def whatsapp_incoming(request):
    """Twilio calls this endpoint for every inbound WhatsApp message."""
    from_raw = request.POST.get("From", "")
    to_raw   = request.POST.get("To", "")
    body     = (request.POST.get("Body") or "").strip()
    msg_sid  = request.POST.get("MessageSid", "")

    from_number = _strip_prefix(from_raw)
    to_number   = _strip_prefix(to_raw)

    business_client = _find_business_client(to_number)
    if not business_client:
        logger.warning("Inbound WhatsApp to %s — no matching tenant.", to_number)
        return _empty_response()

    customer = _find_or_stub_customer(business_client, from_number)

    # One conversation per sender number
    conversation, _ = Conversation.objects.get_or_create(
        business_client=business_client,
        channel="whatsapp",
        external_thread_id=from_number,
        defaults={
            "customer": customer,
            "language": business_client.interface_language or "en",
        },
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
        provider_message_id=msg_sid,
        raw_payload=dict(request.POST.items()),
    )

    if not body:
        return _empty_response()

    # AI agent
    result = None
    try:
        result = handle_inbound_text(
            business_client,
            body,
            conversation=conversation,
            customer=customer,
            channel="whatsapp",
            payload={"from_number": from_number},
            include_voice=False,
            external_thread_id=from_number,
            record_messages=False,  # we already persisted inbound above
        )
        response_text = (result.get("response_text") or "").strip()
    except Exception as exc:
        logger.exception("AI agent failed for WhatsApp from %s: %s", from_number, exc)
        response_text = ""

    if not response_text:
        response_text = "Thanks! We'll get back to you shortly."

    Message.objects.create(
        conversation=conversation,
        direction="outbound",
        message_type="text",
        sender_label="Kaleya",
        body=response_text,
    )

    return _twiml_msg(response_text)
