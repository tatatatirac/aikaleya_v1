"""
Telnyx TeXML voice webhooks.

Endpoints:
  POST /api/telnyx/voice/inbound/   — called when call arrives (returns TeXML greeting)
  POST /api/telnyx/voice/gather/    — called with speech transcript (returns TeXML response)

Telnyx Voice App must be configured as TeXML type (not Call Control).
Set the TeXML URL to: https://aikaleya.com/api/telnyx/voice/inbound/
"""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from billing.services import limits_for_client
from communications.models import CallSession
from telnyx.models import business_client_for_number
from telnyx.services.tts import audio_url as tts_audio_url, generate_response_audio
from telnyx.services.voice_pipeline import get_or_create_greeting_url, process_voice_turn

logger = logging.getLogger(__name__)

# Telnyx TeXML uses the same verb set as Twilio TwiML
TEXML_CONTENT_TYPE = "application/xml"

# Language code mapping: our internal → Telnyx ASR language tag
LANGUAGE_TO_TELNYX = {
    "en": "en-US",
    "es": "es-US",
    "fr": "fr-FR",
    "it": "it-IT",
    "de": "de-DE",
    "pt": "pt-BR",
    "ru": "ru-RU",
    "sr": "sr-RS",
    "hr": "hr-HR",
    "bs": "bs-BA",
}

BASE_URL = getattr(settings, "KALEYA_PUBLIC_URL", "https://aikaleya.com")


def _texml(body: str) -> HttpResponse:
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>\n{body}\n</Response>'
    return HttpResponse(xml, content_type=TEXML_CONTENT_TYPE)


def _gather_xml(action_url: str, language: str = "en-US", timeout: int = 10) -> str:
    return (
        f'  <Gather input="speech" action="{action_url}" '
        f'timeout="{timeout}" speechTimeout="auto" '
        f'language="{language}" '
        f'actionOnEmptyResult="true">\n'
        f'  </Gather>\n'
        f'  <Redirect>{BASE_URL}/api/telnyx/voice/inbound/</Redirect>'
    )


def _play_then_gather(audio_url: str, gather_url: str, language: str = "en-US") -> str:
    return (
        f'  <Play>{audio_url}</Play>\n'
        + _gather_xml(gather_url, language)
    )


def _hangup_response(thank_you_audio_url: str = "") -> str:
    if thank_you_audio_url:
        return f'  <Play>{thank_you_audio_url}</Play>\n  <Hangup/>'
    return "  <Hangup/>"


# ── View 1: Inbound call ─────────────────────────────────────────────────────────
@csrf_exempt
def inbound_call(request):
    """
    Telnyx calls this when a new inbound call arrives.
    We respond with TeXML to play the greeting and start listening.
    Telnyx may use GET or POST depending on app config — handle both.
    """
    params = request.POST if request.method == "POST" else request.GET
    from_number = params.get("From", "").strip()
    to_number = params.get("To", "").strip()
    call_sid = params.get("CallSid") or params.get("CallControlId", "")

    logger.info("Inbound call: from=%s to=%s sid=%s", from_number, to_number, call_sid)

    # Find which salon owns this number
    business_client = business_client_for_number(to_number)
    if not business_client:
        logger.warning("No salon found for Telnyx number: %s", to_number)
        return _texml("  <Say>This number is not configured. Goodbye.</Say>\n  <Hangup/>")

    # Plan gate — voice is a Pro+ feature. Starter callers get a polite hangup.
    if not limits_for_client(business_client).allow_phone_calls:
        logger.info(
            "Voice gated by plan: client=%s from=%s sid=%s",
            business_client.id, from_number, call_sid,
        )
        return _texml(
            '  <Say language="en-US">'
            "AI voice answering is not enabled on this plan. "
            "Please upgrade to Pro or message us on WhatsApp."
            "</Say>\n  <Hangup/>"
        )

    # Use voice_language for ASR — this is the language the salon speaks on calls
    language = business_client.voice_language or business_client.interface_language or "en"
    telnyx_lang = LANGUAGE_TO_TELNYX.get(language, "en-US")

    # Generate (cached) greeting audio
    try:
        greeting_url = get_or_create_greeting_url(
            business_client=business_client,
            language=language,
            from_number=from_number,
        )
    except Exception as exc:
        logger.error("Greeting generation failed: %s", exc)
        greeting_url = ""

    gather_url = f"{BASE_URL}/api/telnyx/voice/gather/"

    if greeting_url:
        xml_body = _play_then_gather(greeting_url, gather_url, telnyx_lang)
    else:
        # Fallback: Telnyx built-in TTS for greeting
        salon_name = business_client.public_name or business_client.name
        greeting_text = f"Salon {salon_name}, how can I help?" if language == "en" else f"Salon {salon_name}, izvolite!"
        xml_body = (
            f'  <Say language="{telnyx_lang}">{greeting_text}</Say>\n'
            + _gather_xml(gather_url, telnyx_lang)
        )

    return _texml(xml_body)


# ── View 2: Speech gather result ────────────────────────────────────────────────
@csrf_exempt
def gather_result(request):
    """
    Telnyx calls this after caller finishes speaking.
    SpeechResult contains the transcribed text.
    We process it through Claude + ElevenLabs and return TeXML.
    Handles both GET and POST from Telnyx.
    """
    params = request.POST if request.method == "POST" else request.GET
    speech_text = params.get("SpeechResult", "").strip()
    from_number = params.get("From", "").strip()
    to_number = params.get("To", "").strip()
    call_sid = params.get("CallSid") or params.get("CallControlId", "")

    logger.info("Gather result: from=%s speech=%r sid=%s", from_number, speech_text[:80], call_sid)

    # Find salon
    business_client = business_client_for_number(to_number)
    if not business_client:
        return _texml("  <Hangup/>")

    # Plan gate — same as inbound; defence in depth in case a session
    # was started before the plan was downgraded.
    if not limits_for_client(business_client).allow_phone_calls:
        return _texml("  <Hangup/>")

    # Handle empty speech (silence / unclear)
    if not speech_text:
        language = business_client.voice_language or business_client.interface_language or "en"
        telnyx_lang = LANGUAGE_TO_TELNYX.get(language, "en-US")
        silence_text = "Sorry, I didn't catch that. Could you repeat?" if language == "en" else "Nisam čula, možete li ponoviti?"
        gather_url = f"{BASE_URL}/api/telnyx/voice/gather/"
        # Use ElevenLabs for silence response (fall back to Telnyx Say)
        silence_audio = ""
        try:
            silence_rel = generate_response_audio(silence_text, call_sid or "silence", 900, language, business_client, add_filler=False)
            silence_audio = tts_audio_url(silence_rel) if silence_rel else ""
        except Exception:
            pass
        if silence_audio:
            xml_body = f'  <Play>{silence_audio}</Play>\n' + _gather_xml(gather_url, telnyx_lang)
        else:
            xml_body = f'  <Say language="{telnyx_lang}">{silence_text}</Say>\n' + _gather_xml(gather_url, telnyx_lang)
        return _texml(xml_body)

    # Run voice pipeline
    try:
        result = process_voice_turn(
            call_sid=call_sid,
            speech_text=speech_text,
            from_number=from_number,
            to_number=to_number,
            business_client=business_client,
        )
    except Exception as exc:
        logger.exception("Voice pipeline error: %s", exc)
        language = business_client.voice_language or business_client.interface_language or "en"
        telnyx_lang = LANGUAGE_TO_TELNYX.get(language, "en-US")
        err_text = "I'm having a technical issue. Please call back in a moment." if language == "en" else "Imam tehničku grešku. Molim pozovite malo kasnije."
        return _texml(f'  <Say language="{telnyx_lang}">{err_text}</Say>\n  <Hangup/>')

    language = result.get("language", "en")
    telnyx_lang = LANGUAGE_TO_TELNYX.get(language, "en-US")
    response_audio_url = result.get("audio_url", "")
    is_done = result.get("is_done", False)

    if is_done:
        if response_audio_url:
            return _texml(f"  <Play>{response_audio_url}</Play>\n  <Hangup/>")
        return _texml("  <Hangup/>")

    gather_url = f"{BASE_URL}/api/telnyx/voice/gather/"

    if response_audio_url:
        return _texml(_play_then_gather(response_audio_url, gather_url, telnyx_lang))

    # Fallback: Telnyx TTS (no ElevenLabs audio generated)
    fallback = "One moment please." if language == "en" else "Molim sačekajte."
    return _texml(
        f'  <Say language="{telnyx_lang}">{fallback}</Say>\n'
        + _gather_xml(gather_url, telnyx_lang)
    )
