"""Twilio voice + SMS layer for Kaleya.

The webhook flow is intentionally minimal:
1. Caller dials a Twilio number → /api/communications/voice/incoming/
2. We respond with TwiML: <Say> greeting + <Gather input="speech">
3. Twilio recognises speech and posts to /api/communications/voice/gather/<session_id>/
4. We run handle_inbound_text(...) → get response text → respond with another
   <Say>/<Play> + <Gather> until the caller hangs up
5. /api/communications/voice/status/<session_id>/ finalises the CallSession

For TTS we default to Twilio's built-in Polly voice (works out of the box).
If the tenant has ElevenLabs configured we generate a short MP3, save it
to /media/twilio_audio/, and use <Play>.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from clients.models import BusinessClient
from communications.models import CallSession, Conversation, Message
from integrations.models import IntegrationConnection


logger = logging.getLogger(__name__)

# Default Twilio voice if ElevenLabs is not configured. Polly.Joanna is American English.
DEFAULT_TWILIO_VOICE = "Polly.Joanna-Neural"

# Polly voice by language (used when ElevenLabs is unavailable)
POLLY_VOICE_BY_LANG = {
    "en": "Polly.Joanna-Neural",
    "en-gb": "Polly.Amy-Neural",
    "es": "Polly.Lucia-Neural",
    "pt": "Polly.Camila-Neural",
    "ru": "Polly.Tatyana",
    "fr": "Polly.Lea-Neural",
    "it": "Polly.Bianca-Neural",
    "de": "Polly.Vicki-Neural",
    "sr": "Polly.Lucia-Neural",  # fallback to similar Slavic-friendly voice
}

# Twilio speech-recognition language codes for <Gather input="speech">
TWILIO_SPEECH_LANG = {
    "en": "en-US",
    "en-gb": "en-GB",
    "es": "es-US",
    "pt": "pt-BR",
    "ru": "ru-RU",
    "fr": "fr-FR",
    "it": "it-IT",
    "de": "de-DE",
    "sr": "sr-RS",
}


def public_base_url() -> str:
    return getattr(settings, "KALEYA_PUBLIC_BASE_URL", "https://www.aikaleya.com").rstrip("/")


def find_business_client_by_called_number(to_number: str) -> BusinessClient | None:
    """Look up which Kaleya tenant owns the dialed Twilio number."""
    if not to_number:
        return None
    cleaned = to_number.strip()
    qs = (
        IntegrationConnection.objects.select_related("business_client")
        .filter(provider="phone", public_number=cleaned)
        .first()
    )
    if qs and qs.business_client:
        return qs.business_client
    # Fallback to the first BusinessClient (only useful while we have one tenant)
    if not BusinessClient.objects.exists():
        return None
    return BusinessClient.objects.first()


def ensure_voice_conversation(business_client: BusinessClient, call_session: CallSession) -> Conversation:
    """Create or fetch the conversation that backs this phone call."""
    conv = Conversation.objects.filter(
        business_client=business_client,
        channel="phone",
        external_thread_id=call_session.external_call_id,
    ).first()
    if conv:
        return conv
    conv = Conversation.objects.create(
        business_client=business_client,
        channel="phone",
        status="open",
        external_thread_id=call_session.external_call_id,
        language=business_client.interface_language or "en",
        metadata={"from_number": call_session.from_number, "to_number": call_session.to_number},
    )
    call_session.conversation = conv
    call_session.save(update_fields=["conversation"])
    return conv


def localized_greeting(business_client: BusinessClient) -> str:
    """Short greeting Kaleya says when picking up."""
    lang = business_client.interface_language or business_client.language or "en"
    name = (business_client.public_name or business_client.name or "").strip() or "the shop"
    greetings = {
        "en": f"Thanks for calling {name}. This is Kaleya, the AI receptionist. How can I help you today?",
        "en-gb": f"Thanks for calling {name}. This is Kaleya, the AI receptionist. How can I help?",
        "es": f"Gracias por llamar a {name}. Soy Kaleya, la recepcionista IA. ¿En qué puedo ayudarte?",
        "pt": f"Obrigada por ligar para {name}. Sou a Kaleya, a recepcionista IA. Como posso ajudar?",
        "ru": f"Спасибо, что позвонили в {name}. Это Калея, ИИ-администратор. Чем могу помочь?",
        "fr": f"Merci d'appeler {name}. Ici Kaleya, la réceptionniste IA. Comment puis-je vous aider ?",
        "it": f"Grazie per aver chiamato {name}. Sono Kaleya, la receptionist IA. Come posso aiutarti?",
        "de": f"Danke für Ihren Anruf bei {name}. Hier ist Kaleya, die KI-Empfangsdame. Wie kann ich helfen?",
        "sr": f"Hvala što ste pozvali {name}. Ja sam Kaleya, AI recepcionerka. Kako mogu da pomognem?",
    }
    return greetings.get(lang) or greetings["en"]


def fallback_no_input_text(business_client: BusinessClient) -> str:
    lang = business_client.interface_language or business_client.language or "en"
    msgs = {
        "en": "Sorry, I didn't catch that. Could you repeat please?",
        "en-gb": "Sorry, I didn't catch that. Could you repeat please?",
        "es": "Perdón, no te escuché. ¿Podrías repetir?",
        "pt": "Desculpa, não percebi. Podes repetir?",
        "ru": "Извините, не услышала. Повторите, пожалуйста.",
        "fr": "Désolée, je n'ai pas compris. Pouvez-vous répéter ?",
        "it": "Scusa, non ho capito. Puoi ripetere?",
        "de": "Entschuldigung, das habe ich nicht verstanden. Können Sie das wiederholen?",
        "sr": "Izvinite, nisam razumela. Možete li ponoviti?",
    }
    return msgs.get(lang) or msgs["en"]


def build_voice_response_twiml(
    business_client: BusinessClient,
    text_to_say: str,
    next_action_url: str,
    *,
    bye: bool = False,
) -> str:
    """Build a TwiML response: <Say>/<Play> + <Gather> for the next turn, or <Hangup>."""
    from xml.sax.saxutils import escape

    lang = business_client.interface_language or business_client.language or "en"
    polly = POLLY_VOICE_BY_LANG.get(lang, DEFAULT_TWILIO_VOICE)
    twilio_lang = TWILIO_SPEECH_LANG.get(lang, "en-US")

    safe_text = escape(text_to_say or "")

    if bye:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'<Say voice="{polly}" language="{twilio_lang}">{safe_text}</Say>'
            "<Hangup/>"
            "</Response>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'<Say voice="{polly}" language="{twilio_lang}">{safe_text}</Say>'
        f'<Gather input="speech" action="{escape(next_action_url)}" method="POST" '
        f'language="{twilio_lang}" speechTimeout="auto" speechModel="experimental_conversations" '
        'timeout="6">'
        '</Gather>'
        f'<Say voice="{polly}" language="{twilio_lang}">{escape(fallback_no_input_text(business_client))}</Say>'
        f'<Redirect method="POST">{escape(next_action_url)}</Redirect>'
        "</Response>"
    )


def gather_action_url(session_id: int) -> str:
    """Absolute URL Twilio posts to after capturing speech."""
    path = reverse("voice-gather", kwargs={"session_id": session_id})
    return f"{public_base_url()}{path}"


def status_callback_url(session_id: int) -> str:
    path = reverse("voice-status", kwargs={"session_id": session_id})
    return f"{public_base_url()}{path}"


# ───── SMS helper ──────────────────────────────────────────────────────────

def _twilio_credentials():
    sid = getattr(settings, "KALEYA_TWILIO_ACCOUNT_SID", "")
    token = getattr(settings, "KALEYA_TWILIO_AUTH_TOKEN", "")
    from_number = getattr(settings, "KALEYA_TWILIO_PHONE_NUMBER", "")
    return sid, token, from_number


def send_sms(business_client: BusinessClient, to_number: str, body: str) -> dict:
    """Send an SMS via Twilio. Returns dict with 'sid' or 'error' key."""
    sid, token, default_from = _twilio_credentials()

    # Prefer tenant's own Twilio "phone" integration if it has a number stored
    integration = (
        IntegrationConnection.objects.filter(
            business_client=business_client, provider="phone", enabled=True
        )
        .first()
    )
    from_number = (integration.public_number if integration and integration.public_number else default_from) or ""

    if not (sid and token and from_number and to_number and body):
        return {"error": "Twilio credentials, from-number, or message missing."}

    try:
        from twilio.rest import Client
    except ImportError:
        return {"error": "twilio SDK not installed (pip install twilio)."}

    try:
        client = Client(sid, token)
        message = client.messages.create(body=body, from_=from_number, to=to_number)
        return {"sid": message.sid, "status": message.status, "from": from_number, "to": to_number}
    except Exception as exc:
        logger.warning("Twilio SMS send failed: %s", exc)
        return {"error": str(exc)}
