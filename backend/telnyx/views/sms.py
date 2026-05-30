"""
Telnyx SMS webhook.

Inbound SMS → existing ai_agent workflow → reply via Telnyx SMS API.
This reuses the full text-channel agent (intent detection, booking, memory, etc.)
"""

import json
import logging
from urllib import error, request as urllib_request

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from telnyx.models import business_client_for_number

logger = logging.getLogger(__name__)


def _send_sms(to: str, from_: str, body: str) -> bool:
    """Send SMS via Telnyx API v2."""
    api_key = settings.KALEYA_TELNYX_API_KEY
    if not api_key:
        logger.error("TELNYX_API_KEY not configured")
        return False

    messaging_profile_id = settings.KALEYA_TELNYX_MESSAGING_PROFILE_ID

    payload = json.dumps({
        "from": from_,
        "to": to,
        "text": body,
        **({"messaging_profile_id": messaging_profile_id} if messaging_profile_id else {}),
    }).encode("utf-8")

    req = urllib_request.Request(
        "https://api.telnyx.com/v2/messages",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as resp:
            return resp.status in (200, 201, 202)
    except error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")
        logger.error("Telnyx SMS send HTTP %s: %s", exc.code, body_err)
        return False
    except error.URLError as exc:
        logger.error("Telnyx SMS send error: %s", exc)
        return False


@csrf_exempt
@require_POST
def inbound_sms(request):
    """
    Telnyx POSTs here when an SMS arrives on one of our numbers.
    We pass it through the existing ai_agent workflow and reply.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({"error": "invalid json"}, status=400)

    # Telnyx SMS webhook payload structure
    event_type = data.get("data", {}).get("event_type", "")
    if event_type != "message.received":
        return JsonResponse({"ok": True})  # Ignore delivery reports etc.

    payload = data.get("data", {}).get("payload", {})
    from_number = (payload.get("from") or {}).get("phone_number", "")
    to_data = payload.get("to") or [{}]
    to_number = to_data[0].get("phone_number", "") if to_data else ""
    message_text = payload.get("text", "").strip()
    message_id = payload.get("id", "")

    logger.info("Inbound SMS: from=%s to=%s text=%r", from_number, to_number, message_text[:80])

    if not message_text or not from_number:
        return JsonResponse({"ok": True})

    # Find salon
    business_client = business_client_for_number(to_number)
    if not business_client:
        logger.warning("No salon for Telnyx number: %s", to_number)
        return JsonResponse({"ok": True})

    # Run through existing AI agent workflow (same as WhatsApp/web channels)
    try:
        from ai_agent.views import run_workflow_for_channel
        reply_text = run_workflow_for_channel(
            business_client=business_client,
            message_text=message_text,
            channel="sms",
            external_thread_id=from_number,
            from_number=from_number,
        )
    except Exception as exc:
        logger.exception("SMS workflow error: %s", exc)
        reply_text = ""

    if reply_text:
        _send_sms(to=from_number, from_=to_number, body=reply_text)

    return JsonResponse({"ok": True})


@csrf_exempt
@require_POST
def sms_status(request):
    """
    Telnyx delivery status callback.
    We just log it for now — can be used for retry logic later.
    """
    try:
        data = json.loads(request.body)
        event_type = data.get("data", {}).get("event_type", "")
        logger.debug("SMS status event: %s", event_type)
    except Exception:
        pass
    return JsonResponse({"ok": True})
