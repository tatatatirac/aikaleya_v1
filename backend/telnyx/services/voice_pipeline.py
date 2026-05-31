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

# Valid workflow states (must match KALEYA_VOICE_SOUL_* state machine)
VALID_VOICE_STATES = {"greeting", "slot_offer", "confirm", "booked", "done"}


def _parse_action_tags(text: str) -> tuple[dict, str]:
    """
    Extracts ALL [TAG: ...] tags from Claude's response.

    Returns (tags_dict, clean_text) where tags_dict may contain:
      - "STATE":    str    (next workflow state)
      - "BOOK":     dict   (booking params: service/date/time/phone)
      - "HANGUP":   True   (call should end)
      - "TRANSFER": True   (caller wants a human)
    clean_text has ALL tags stripped (caller never hears them).
    """
    tags: dict = {}
    for m in ACTION_TAG_PATTERN.finditer(text):
        action = m.group("action").upper()
        params_str = (m.group("params") or "").strip()
        if action == "STATE":
            tags["STATE"] = params_str.strip()
        elif action == "BOOK":
            params: dict = {}
            for part in params_str.split():
                if "=" in part:
                    k, v = part.split("=", 1)
                    params[k.strip()] = v.strip()
            tags["BOOK"] = params
        elif action == "HANGUP":
            tags["HANGUP"] = True
        elif action == "TRANSFER":
            tags["TRANSFER"] = True

    # Strip all tags from the spoken text
    clean = ACTION_TAG_PATTERN.sub("", text).strip()
    # Collapse leftover double spaces from tag removal
    clean = re.sub(r"\s+", " ", clean).strip()
    return tags, clean


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
        "max_tokens": 150,   # Voice responses must be SHORT — shorter = faster TTS
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
    import time
    t_start = time.monotonic()
    timings = {}

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
    customer_name = _real_customer_name(customer)
    # Pull last service this caller booked (for returning-customer greeting shortcut)
    last_service_hint = state.get("last_service_hint", "") or _lookup_last_service(customer)

    # ── Fetch available slots (cached in session for the call) ─────────────────
    service_hint = state.get("service_hint", "")
    cached_slots = state.get("slots_cache")
    cached_for_service = state.get("slots_cache_service", "")
    # Re-fetch only if first turn or service hint changed
    if not cached_slots or cached_for_service != service_hint:
        t = time.monotonic()
        slots = _fetch_slots_context(business_client, service_hint, language)
        timings["slots"] = round((time.monotonic() - t) * 1000)
        state["slots_cache"] = slots
        state["slots_cache_service"] = service_hint
    else:
        slots = cached_slots
        timings["slots"] = 0

    # ── Workflow state (state machine matches KALEYA_VOICE_SOUL_* template) ────
    voice_state = state.get("voice_state", "greeting")

    # ── Build system prompt ─────────────────────────────────────────────────────
    system_prompt = build_voice_prompt(
        business_client,
        language=language,
        customer_name=customer_name,
        slots=slots,
        caller_phone=from_number,
        voice_state=voice_state,
        last_service_hint=last_service_hint,
    )

    # ── Load conversation history ───────────────────────────────────────────────
    history = state.get("history", [])

    # ── Call Claude ─────────────────────────────────────────────────────────────
    t = time.monotonic()
    raw_response = _call_claude_voice(system_prompt, history, speech_text)
    timings["claude"] = round((time.monotonic() - t) * 1000)

    # ── Parse ALL tags (STATE / BOOK / HANGUP / TRANSFER may co-exist) ─────────
    tags, clean_response = _parse_action_tags(raw_response)

    # ── State transition ────────────────────────────────────────────────────────
    next_state = tags.get("STATE", "").strip().lower()
    if next_state in VALID_VOICE_STATES:
        state["voice_state"] = next_state

    # ── Execute booking action ──────────────────────────────────────────────────
    is_done = False
    transfer = False

    book_params = tags.get("BOOK")
    if book_params:
        _execute_voice_booking(business_client, book_params, customer, from_number, session)
        state["voice_state"] = "booked"
        # Remember service for returning-caller shortcut next time
        if book_params.get("service"):
            state["last_service_hint"] = book_params["service"]

    if tags.get("HANGUP"):
        is_done = True
        state["voice_state"] = "done"

    if tags.get("TRANSFER"):
        transfer = True
        is_done = True

    # ── Update conversation history ─────────────────────────────────────────────
    history.append({"role": "user", "content": speech_text})
    history.append({"role": "assistant", "content": clean_response})
    # Keep last 12 turns in history (6 exchanges) to stay within token limits
    state["history"] = history[-12:]
    state["turn"] = turn
    if book_params and book_params.get("service"):
        state["service_hint"] = book_params["service"]

    # ── Generate TTS audio ──────────────────────────────────────────────────────
    t = time.monotonic()
    rel_path = generate_response_audio(
        text=clean_response,
        call_sid=call_sid,
        turn=turn,
        language=language,
        business_client=business_client,
    )
    timings["tts"] = round((time.monotonic() - t) * 1000)
    full_audio_url = audio_url(rel_path) if rel_path else ""
    timings["total"] = round((time.monotonic() - t_start) * 1000)
    import logging as _l
    _l.getLogger(__name__).info("Voice turn timings (ms): %s", timings)

    # ── Save transcript snippet ─────────────────────────────────────────────────
    transcript_line = f"[{turn}] Caller: {speech_text}\n    Kaleya: {clean_response}\n"
    session.transcript = (session.transcript or "") + transcript_line
    session.metadata = state
    if is_done:
        session.status = "completed"
        session.ended_at = timezone.now()
    session.save(update_fields=["transcript", "metadata", "status", "ended_at"])

    # NOTE: Do NOT cleanup audio here — Telnyx fetches the file AFTER we return
    # the TeXML response. Cleaning up now would cause a 404 and robotic error.
    # Audio files are cleaned up periodically by cron or admin command.

    return {
        "audio_url": full_audio_url,
        "is_done": is_done,
        "transfer": transfer,
        "language": language,
        "turn": turn,
    }


PLACEHOLDER_NAMES = {"phone caller", "phonecaller", "unknown", "anonymous", ""}


def _real_customer_name(customer) -> str:
    """Return the customer's name only if it's not a placeholder (e.g. 'Phone Caller')."""
    if not customer:
        return ""
    name = (customer.full_name or "").strip()
    if name.lower() in PLACEHOLDER_NAMES:
        return ""
    # Also skip if first_name is the placeholder
    first = (getattr(customer, "first_name", "") or "").strip().lower()
    if first in {"phone caller", "phonecaller"}:
        return ""
    return name


def _lookup_last_service(customer) -> str:
    """
    Returns the service name from this customer's most recent appointment,
    so Kaleya can offer "same as last time?" to returning callers.
    Returns "" if customer is unknown or has no appointment history.
    """
    if not customer:
        return ""
    try:
        from appointments.models import Appointment
        last = (
            Appointment.objects
            .filter(customer=customer, service__isnull=False)
            .select_related("service")
            .order_by("-date", "-start_time")
            .first()
        )
        if last and last.service:
            return last.service.name
    except Exception:
        pass
    return ""


def get_or_create_greeting_url(business_client, language: str = "en", from_number: str = "") -> str:
    """
    Returns URL for the salon's greeting audio.
    Generates and caches if not already done.
    """
    from ai_agent.prompts import build_voice_greeting

    customer = find_customer_by_payload_identity(business_client, {"phone": from_number}) if from_number else None
    customer_name = _real_customer_name(customer)

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
