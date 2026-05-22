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

# Default Twilio voice if ElevenLabs is not configured.
# Google's Neural2 voices are the most human-sounding TTS Twilio offers (better than Polly).
DEFAULT_TWILIO_VOICE = "Google.en-US-Neural2-F"

# Best-available Twilio neural voice by language (used when ElevenLabs is unavailable).
# en/en-gb/de/fr/es/it/pt/ru get Google Neural2 — much more natural than Polly.
# sr/hr/bs has no native Twilio voice — we fall back to a multilingual model.
POLLY_VOICE_BY_LANG = {
    "en":    "Google.en-US-Neural2-F",
    "en-gb": "Google.en-GB-Neural2-A",
    "es":    "Google.es-ES-Neural2-A",
    "pt":    "Google.pt-PT-Wavenet-A",
    "ru":    "Google.ru-RU-Wavenet-C",
    "fr":    "Google.fr-FR-Neural2-A",
    "it":    "Google.it-IT-Neural2-A",
    "de":    "Google.de-DE-Neural2-C",
    "sr":    "Google.en-US-Neural2-F",  # No native Serbian; fall back to English voice
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


def _try_elevenlabs_audio_url(business_client: BusinessClient, text: str, language: str = "") -> str | None:
    """Generate ElevenLabs MP3 and return absolute public URL. None if ElevenLabs unavailable."""
    if not text or not text.strip():
        return None
    try:
        from ai_agent.providers import synthesize_elevenlabs_speech
        lang = language or business_client.interface_language or business_client.language or "en"
        result = synthesize_elevenlabs_speech(business_client, text, language=lang)
        rel_url = result.get("audio_url") or ""
        if not rel_url:
            return None
        if rel_url.startswith("http"):
            return rel_url
        # Make absolute — Twilio needs full URL for <Play>
        return f"{public_base_url()}/{rel_url.lstrip('/')}"
    except Exception as exc:
        logger.warning("ElevenLabs TTS failed, falling back to Google voice: %s", exc)
        return None


def _say_or_play(business_client: BusinessClient, text: str, polly_voice: str, twilio_lang: str) -> str:
    """Return either a <Play> tag (ElevenLabs MP3) or <Say> tag (Twilio TTS)."""
    from xml.sax.saxutils import escape

    audio_url = _try_elevenlabs_audio_url(business_client, text)
    if audio_url:
        return f'<Play>{escape(audio_url)}</Play>'
    return f'<Say voice="{polly_voice}" language="{twilio_lang}">{escape(text or "")}</Say>'


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

    main_voice = _say_or_play(business_client, text_to_say, polly, twilio_lang)
    fallback_voice = _say_or_play(business_client, fallback_no_input_text(business_client), polly, twilio_lang)

    if bye:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            f'{main_voice}'
            "<Hangup/>"
            "</Response>"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f'{main_voice}'
        f'<Gather input="speech" action="{escape(next_action_url)}" method="POST" '
        f'language="{twilio_lang}" speechTimeout="auto" speechModel="experimental_conversations" '
        'timeout="6">'
        '</Gather>'
        f'{fallback_voice}'
        f'<Redirect method="POST">{escape(next_action_url)}</Redirect>'
        "</Response>"
    )


def build_transfer_twiml(business_client: BusinessClient, forward_to: str, twilio_number: str = "") -> str:
    """TwiML that bridges the caller to the owner's phone.

    Flow:
      1. <Say> "hold" message in the tenant's language
      2. <Dial> the owner (30-second ring, record the bridged call)
      3. If the owner doesn't answer → <Say> "no one available" + <Hangup>
    """
    from xml.sax.saxutils import escape

    lang = business_client.interface_language or business_client.language or "en"
    polly = POLLY_VOICE_BY_LANG.get(lang, DEFAULT_TWILIO_VOICE)
    twilio_lang = TWILIO_SPEECH_LANG.get(lang, "en-US")

    hold_msgs = {
        "en":    "One moment, connecting you to the salon now.",
        "en-gb": "One moment, connecting you to the salon now.",
        "es":    "Un momento, te estoy conectando con el salón ahora.",
        "pt":    "Um momento, estou a conectar-te com o salão agora.",
        "ru":    "Одну минуту, соединяю вас с салоном.",
        "fr":    "Un instant, je vous mets en relation avec le salon.",
        "it":    "Un momento, ti sto mettendo in contatto con il salone.",
        "de":    "Einen Moment, ich verbinde Sie jetzt mit dem Salon.",
        "sr":    "Trenutak, prenosim vas na salon.",
    }
    no_answer_msgs = {
        "en":    "I'm sorry, no one is available right now. We'll call you back shortly. Goodbye!",
        "en-gb": "I'm sorry, no one is available right now. We'll call you back shortly. Goodbye!",
        "es":    "Lo siento, no hay nadie disponible ahora mismo. Te llamaremos pronto. ¡Adiós!",
        "pt":    "Desculpa, não há ninguém disponível agora. Ligamos-te em breve. Adeus!",
        "ru":    "Извините, сейчас никого нет. Мы перезвоним вам в ближайшее время. До свидания!",
        "fr":    "Je suis désolée, personne n'est disponible pour le moment. Nous vous rappellerons. Au revoir !",
        "it":    "Mi dispiace, nessuno è disponibile al momento. Ti richiameremo presto. Arrivederci!",
        "de":    "Es tut mir leid, niemand ist gerade erreichbar. Wir rufen Sie zurück. Auf Wiedersehen!",
        "sr":    "Žao mi je, niko nije dostupan. Javićemo vam se uskoro. Doviđenja!",
    }

    hold_text = hold_msgs.get(lang, hold_msgs["en"])
    no_answer_text = no_answer_msgs.get(lang, no_answer_msgs["en"])

    hold_voice = _say_or_play(business_client, hold_text, polly, twilio_lang)
    no_answer_voice = _say_or_play(business_client, no_answer_text, polly, twilio_lang)

    # callerId must be a Twilio-verified number — use the tenant's Kaleya number
    caller_id_attr = f' callerId="{escape(twilio_number)}"' if twilio_number else ""

    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{hold_voice}"
        f'<Dial{caller_id_attr} timeout="30" record="record-from-answer">'
        f"{escape(forward_to)}"
        f"</Dial>"
        f"{no_answer_voice}"
        "<Hangup/>"
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
