"""Twilio Voice webhook endpoints.

All three views are CSRF-exempt and auth-free — Twilio is the caller.
We can later add Twilio request validation via X-Twilio-Signature.
"""

import logging
from datetime import datetime, timezone

from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ai_agent.services import handle_inbound_text
from communications.models import CallSession, Message
from communications.twilio_service import (
    build_voice_response_twiml,
    ensure_voice_conversation,
    find_business_client_by_called_number,
    gather_action_url,
    localized_greeting,
    status_callback_url,
)


logger = logging.getLogger(__name__)


def _twiml(xml: str) -> HttpResponse:
    return HttpResponse(xml, content_type="application/xml")


@csrf_exempt
@require_POST
def voice_incoming(request):
    """Twilio hits this when a caller dials our number."""
    call_sid = request.POST.get("CallSid", "")
    from_number = request.POST.get("From", "")
    to_number = request.POST.get("To", "")

    business_client = find_business_client_by_called_number(to_number)
    if not business_client:
        logger.warning("Incoming call to %s — no matching tenant, hanging up.", to_number)
        return _twiml(
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response><Say>Sorry, this number is not active yet.</Say><Hangup/></Response>"
        )

    session = CallSession.objects.create(
        business_client=business_client,
        provider="twilio",
        external_call_id=call_sid,
        status="active",
        from_number=from_number,
        to_number=to_number,
        started_at=datetime.now(timezone.utc),
        metadata={"raw_incoming": dict(request.POST.items())},
    )
    ensure_voice_conversation(business_client, session)

    greeting = localized_greeting(business_client)
    twiml = build_voice_response_twiml(
        business_client,
        greeting,
        gather_action_url(session.id),
    )
    # Include status callback so Twilio reports back when the call ends.
    # We can't easily inject statusCallback into TwiML once a call is in progress,
    # so it must be configured on the Twilio number itself or via API. Logged for ops.
    return _twiml(twiml)


@csrf_exempt
@require_POST
def voice_gather(request, session_id):
    """Twilio posts here after capturing the caller's speech."""
    speech_result = request.POST.get("SpeechResult", "").strip()
    confidence = request.POST.get("Confidence", "")

    session = CallSession.objects.select_related("business_client", "conversation").filter(id=session_id).first()
    if not session:
        return HttpResponseBadRequest("Unknown session")

    business_client = session.business_client
    conversation = session.conversation or ensure_voice_conversation(business_client, session)

    if not speech_result:
        # Caller stayed silent — ask again
        twiml = build_voice_response_twiml(
            business_client,
            "I didn't catch that. Could you tell me how I can help?",
            gather_action_url(session.id),
        )
        return _twiml(twiml)

    # Persist inbound speech as a message and accumulate to the call transcript
    Message.objects.create(
        conversation=conversation,
        direction="inbound",
        message_type="voice",
        sender_label=session.from_number or "Caller",
        body=speech_result,
        raw_payload={"confidence": confidence},
    )
    transcript_chunk = f"\n[caller] {speech_result}"
    if session.transcript:
        session.transcript = (session.transcript + transcript_chunk)[:8000]
    else:
        session.transcript = transcript_chunk.lstrip()

    try:
        result = handle_inbound_text(
            business_client,
            speech_result,
            conversation=conversation,
            channel="phone",
            payload={"from_number": session.from_number},
            include_voice=False,
            external_thread_id=session.external_call_id,
            record_messages=False,  # we record manually above to control flow
        )
        response_text = (result.get("response_text") or "").strip() or "Let me get back to you on that."
    except Exception as exc:
        logger.exception("AI agent failed during voice call: %s", exc)
        response_text = "I'm having trouble understanding. Let me get someone to call you back."

    # Persist outbound AI message
    Message.objects.create(
        conversation=conversation,
        direction="outbound",
        message_type="voice",
        sender_label="Kaleya",
        body=response_text,
    )
    session.transcript = (session.transcript + f"\n[kaleya] {response_text}")[:8000]
    session.save(update_fields=["transcript"])

    # Naive ending heuristic — if AI's response signals goodbye, hang up.
    bye_signals = ("goodbye", "have a great", "see you", "bye for now", "talk soon")
    bye = any(sig in response_text.lower() for sig in bye_signals)

    twiml = build_voice_response_twiml(
        business_client,
        response_text,
        gather_action_url(session.id),
        bye=bye,
    )
    return _twiml(twiml)


@csrf_exempt
@require_POST
def voice_status(request, session_id):
    """Twilio posts here when the call ends (configured on the number)."""
    session = CallSession.objects.filter(id=session_id).first()
    if not session:
        return HttpResponse("ok")

    call_status = request.POST.get("CallStatus", "")
    call_duration = request.POST.get("CallDuration", "0")
    recording_url = request.POST.get("RecordingUrl", "")

    status_map = {
        "completed": "completed",
        "no-answer": "missed",
        "busy": "missed",
        "failed": "failed",
        "canceled": "missed",
    }
    new_status = status_map.get(call_status, session.status)

    session.status = new_status
    session.ended_at = datetime.now(timezone.utc)
    if recording_url:
        session.recording_url = recording_url
    md = dict(session.metadata or {})
    md["twilio_call_status"] = call_status
    md["twilio_duration_seconds"] = call_duration
    session.metadata = md
    session.save(update_fields=["status", "ended_at", "recording_url", "metadata"])

    if session.conversation:
        session.conversation.status = "closed"
        session.conversation.save(update_fields=["status"])

    return HttpResponse("ok")
