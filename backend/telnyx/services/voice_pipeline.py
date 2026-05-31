"""
Kaleya Voice AI Pipeline — Phase B1

Flow per conversation turn:
  Speech text → detect language → Claude (voice prompt) → parse action → TTS → MP3 URL

Claude uses a voice-specific system prompt that instructs it to:
  - Respond naturally and briefly (1-2 sentences)
  - Append [ACTION: ...] tags when booking/hanging up
  - Behave as Kaleya the receptionist

We strip [ACTION: ...] from TTS and execute booking/hangup separately.
"""

import json
import re
from datetime import date, timedelta
from urllib import error, request as urllib_request

from django.conf import settings
from django.utils import timezone

from ai_agent.prompts import build_voice_prompt
from ai_agent.services import detect_message_language, find_customer_by_payload_identity
from ai_agent.tools import check_availability_tool, book_appointment_tool, client_local_today
from communications.models import CallSession, Conversation
from telnyx.services.tts import generate_response_audio, generate_greeting, cleanup_call_audio, audio_url


# ── Action tag parser ───────────────────────────────────────────────────────────
ACTION_TAG_PATTERN = re.compile(r"\[(?P<action>[A-Z]+)(?::(?P<params>[^\]]*))?\]", re.IGNORECASE)


def _parse_action(text: str) -> tuple[str, dict, str]:
    """
    Extracts the last [ACTION: ...] tag from Claude's response.
    Returns (action_name, params_dict, clean_text).
    action_name is one of: "BOOK", "HANGUP", "TRANSFER", or "" (none).
    clean_text has the action tag stripped out.
    """
    match = None
    for m in ACTION_TAG_PATTERN.finditer(text):
        match = m

    if not match:
        return "", {}, text.strip()

    action = match.group("action").upper()
    params_str = match.group("params") or ""
    params = {}
    for part in params_str.split():
        if "=" in part:
            k, v = part.split("=", 1)
            params[k.strip()] = v.strip()

    clean_text = text[: match.start()].strip()
    return action, params, clean_text


# ── Slots formatter (injects available slots into Claude context) ───────────────
def _fetch_slots_context(business_client, service_hint: str = "", language: str = "en") -> dict:
    """
    Fetches available slots for today and tomorrow.
    Returns dict with 'today' and 'tomorrow' slot lists.
    """
    today = client_local_today(business_client)
    tomorrow = today + timedelta(days=1)
    result = {"today": [], "tomorrow": [], "time_morning": "", "time_afternoon": ""}

    for target_date, key in ((today, "today"), (tomorrow, "tomorrow")):
        try:
            output = check_availability_tool(
                business_client,
                {"date": target_date.isoformat(), "service_hint": service_hint},
                reference_date=today,
            )
            slots = output.get("suggested_slots") or []
            result[key] = slots[:6]  # max 6 per day
        except Exception:
            result[key] = []

    # Build morning/afternoon pair for today (or tomorrow if today empty)
    for day_key in ("today", "tomorrow"):
        slots = result[day_key]
        if not slots:
            continue
        morning = next((s for s in slots if s < "12:00"), "")
        afternoon = next((s for s in slots if s >= "12:00"), "")
        if morning or afternoon:
            result["time_morning"] = morning or slots[0]
            result["time_afternoon"] = afternoon or (slots[1] if len(slots) > 1 else slots[0])
            break

    return result


def _format_slots_for_prompt(slots: list) -> str:
    if not slots:
        return "fully booked"
    return ", ".join(slots[:5])


# ── Claude voice call ───────────────────────────────────────────────────────────
def _call_claude_voice(
    system_prompt: str,
    conversation_history: list,
    new_message: str,
) -> str:
    """
    Single Claude API call for voice turn.
    Returns Claude's raw response text (may contain [ACTION: ...] tag).
    """
    api_key = settings.KALEYA_ANTHROPIC_API_KEY
    model = settings.KALEYA_ANTHROPIC_MODEL

    if not api_key:
        return "Sorry, the AI system is not configured. Please call back later."

    messages = list(conversation_history) + [{"role": "user", "content": new_message}]

    payload = json.dumps({
        "model": model,
        "max_tokens": 300,   # Voice responses must be SHORT
        "temperature": 0.6,  # Slightly more natural than 0.3
        "system": system_prompt,
        "messages": messages,
    }).encode("utf-8")

    req = urllib_request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data.get("content") or []
            texts = [item.get("text", "") for item in content if item.get("type") == "text"]
            return "\n".join(t for t in texts if t).strip()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Claude HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Claude connection error: {exc}") from exc


# ── Main pipeline entry point ───────────────────────────────────────────────────
def process_voice_turn(
    call_sid: str,
    speech_text: str,
    from_number: str,
    to_number: str,
    business_client,
) -> dict:
    """
    Processes one voice conversation turn.

    Args:
        call_sid:         Telnyx call control ID (used to find CallSession)
        speech_text:      Transcribed speech from caller (Telnyx ASR)
        from_number:      Caller's phone number (E.164)
        to_number:        Salon's Telnyx number (E.164)
        business_client:  BusinessClient instance

    Returns dict:
        audio_url:   Public URL to play (MP3)
        is_done:     True if call should end (booking confirmed / hangup)
        transfer:    True if customer requested human
        language:    Detected language code
        turn:        Turn number
    """
    # ── Load or create CallSession ──────────────────────────────────────────────
    session = CallSession.objects.filter(
        external_call_id=call_sid,
        business_client=business_client,
    ).first()

    if not session:
        # Create new session for this call
        session = CallSession.objects.create(
            business_client=business_client,
            external_call_id=call_sid,
            provider="telnyx",
            from_number=from_number,
            to_number=to_number,
            status="active",
            started_at=timezone.now(),
            metadata={},
        )

    state = session.metadata or {}
    turn = int(state.get("turn", 0)) + 1

    # ── Detect language ─────────────────────────────────────────────────────────
    language = state.get("language") or detect_message_language(speech_text, "en")
    state["language"] = language

    # ── Find customer by caller phone ───────────────────────────────────────────
    customer = find_customer_by_payload_identity(business_client, {"phone": from_number})
    customer_name = customer.full_name if customer else ""

    # ── Fetch available slots ───────────────────────────────────────────────────
    service_hint = state.get("service_hint", "")
    slots = _fetch_slots_context(business_client, service_hint, language)

    # ── Build system prompt ─────────────────────────────────────────────────────
    system_prompt = build_voice_prompt(
        business_client,
        language=language,
        customer_name=customer_name,
        slots=slots,
    )

    # ── Load conversation history ───────────────────────────────────────────────
    history = state.get("history", [])

    # ── Call Claude ─────────────────────────────────────────────────────────────
    raw_response = _call_claude_voice(system_prompt, history, speech_text)

    # ── Parse action tag ────────────────────────────────────────────────────────
    action, params, clean_response = _parse_action(raw_response)

    # ── Execute booking action ──────────────────────────────────────────────────
    is_done = False
    transfer = False

    if action == "BOOK":
        _execute_voice_booking(business_client, params, customer, from_number, session)
        is_done = True

    elif action == "HANGUP":
        is_done = True

    elif action == "TRANSFER":
        transfer = True
        is_done = True

    # ── Update conversation history ─────────────────────────────────────────────
    history.append({"role": "user", "content": speech_text})
    history.append({"role": "assistant", "content": clean_response})
    # Keep last 12 turns in history (6 exchanges) to stay within token limits
    state["history"] = history[-12:]
    state["turn"] = turn
    if params.get("service"):
        state["service_hint"] = params["service"]

    # ── Generate TTS audio ──────────────────────────────────────────────────────
    rel_path = generate_response_audio(
        text=clean_response,
        call_sid=call_sid,
        turn=turn,
        language=language,
        business_client=business_client,
    )
    full_audio_url = audio_url(rel_path) if rel_path else ""

    # ── Save transcript snippet ─────────────────────────────────────────────────
    transcript_line = f"[{turn}] Caller: {speech_text}\n    Kaleya: {clean_response}\n"
    session.transcript = (session.transcript or "") + transcript_line
    session.metadata = state
    if is_done:
        session.status = "completed"
        session.ended_at = timezone.now()
    session.save(update_fields=["transcript", "metadata", "status", "ended_at"])

    # ── Cleanup audio files when done ──────────────────────────────────────────
    if is_done:
        cleanup_call_audio(call_sid)

    return {
        "audio_url": full_audio_url,
        "is_done": is_done,
        "transfer": transfer,
        "language": language,
        "turn": turn,
    }


def get_or_create_greeting_url(business_client, language: str = "en", from_number: str = "") -> str:
    """
    Returns URL for the salon's greeting audio.
    Generates and caches if not already done.
    """
    from ai_agent.prompts import build_voice_greeting

    customer = find_customer_by_payload_identity(business_client, {"phone": from_number}) if from_number else None
    customer_name = customer.full_name if customer else ""

    greeting_text = build_voice_greeting(
        business_client=business_client,
        language=language,
        customer_name=customer_name,
    )

    rel_path = generate_greeting(
        text=greeting_text,
        salon_id=business_client.id,
        language=language,
        business_client=business_client,
    )
    return audio_url(rel_path) if rel_path else ""


def _execute_voice_booking(business_client, params: dict, customer, from_number: str, session: CallSession):
    """
    Executes the actual appointment booking when Claude outputs [BOOK: ...].
    """
    try:
        payload = {
            "service_hint": params.get("service", ""),
            "date": params.get("date", ""),
            "time": params.get("time", ""),
            "phone": params.get("phone", "") or from_number,
            "customer_name": customer.full_name if customer else "",
        }
        result = book_appointment_tool(business_client, payload)
        session.metadata["last_booking"] = result
    except Exception as exc:
        session.metadata["booking_error"] = str(exc)
