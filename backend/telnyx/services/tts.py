"""
ElevenLabs TTS service for voice calls.
Generates MP3 audio files and stores them in MEDIA_ROOT/voice/.
"""

import hashlib
import json
import re
import time
from pathlib import Path
from urllib import error, request as urllib_request

from django.conf import settings


# ── Streaming-friendly voice settings ──────────────────────────────────────────
VOICE_SETTINGS = {
    "stability": 0.35,          # Lower = more expressive, natural (was 0.5)
    "similarity_boost": 0.75,
    "style": 0.15,
    "use_speaker_boost": True,
}

# Aria voice — warm, confident, works well multilingual
# User can override via ELEVENLABS_VOICE_ID in .env
DEFAULT_VOICE_ID = "9BWtsMINqrJLrRacOk9x"  # Aria

# Use turbo model for lower latency (good for real-time calls)
DEFAULT_MODEL = "eleven_turbo_v2_5"


# ── Phone number → natural speech formatter ─────────────────────────────────────
def format_phone_for_speech(phone: str, language: str = "en") -> str:
    """
    Convert E.164 phone number to natural spoken format.
    Prevents ElevenLabs from reading digit-by-digit.

    +381641234567  → "065 123 4567"   (BCS)
    +12125551234   → "212-555-1234"   (EN)
    """
    if not phone:
        return phone
    digits = re.sub(r"\D", "", phone)

    if language in ("sr", "hr", "bs", "bcs") and digits.startswith("381"):
        local = "0" + digits[3:]
        if len(local) == 9:
            return f"{local[:3]} {local[3:6]} {local[6:]}"
        if len(local) == 10:
            return f"{local[:3]} {local[3:7]} {local[7:]}"
        return local

    if language == "en" and len(digits) == 11 and digits.startswith("1"):
        d = digits[1:]
        return f"{d[:3]}-{d[3:6]}-{d[6:]}"

    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"

    return phone


# ── Humanizer ───────────────────────────────────────────────────────────────────
import random

VOICE_FILLERS = {
    "en": ["Sure! ", "Of course! ", "Let me check... ", "Absolutely! "],
    "sr": ["Naravno! ", "Aha! ", "Da da! ", "Sekund... "],
    "hr": ["Naravno! ", "Aha! ", "Da da! ", "Sekundu... "],
    "bs": ["Naravno! ", "Aha! ", "Da da! ", "Sekund... "],
    "es": ["¡Claro! ", "Por supuesto! ", "Déjame ver... "],
    "fr": ["Bien sûr! ", "Absolument! ", "Un instant... "],
    "it": ["Certo! ", "Naturalmente! ", "Un attimo... "],
    "de": ["Natürlich! ", "Klar! ", "Einen Moment... "],
    "pt": ["Claro! ", "Com certeza! ", "Um momento... "],
    "ru": ["Конечно! ", "Одну секунду... ", "Сейчас проверю... "],
}


def add_humanizer_filler(text: str, language: str = "en", probability: float = 0.25) -> str:
    """
    Adds a natural filler phrase at the start of a response.
    Only fires ~25% of the time so it doesn't become annoying.
    Never adds filler to very short responses (one word).
    """
    if len(text.split()) < 3:
        return text
    if random.random() > probability:
        return text
    fillers = VOICE_FILLERS.get(language) or VOICE_FILLERS["en"]
    return random.choice(fillers) + text


# ── Sentence splitter (for future streaming upgrades) ──────────────────────────
def split_into_sentences(text: str) -> list[str]:
    """
    Splits text into sentences for sequential TTS generation.
    Used in Phase B2 streaming to start playing sentence 1
    while sentence 2 is still being generated.
    """
    # Simple sentence splitter — works for English and BCS
    sentences = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip()]


# ── Core TTS function ───────────────────────────────────────────────────────────
def _elevenlabs_tts(text: str, voice_id: str, api_key: str, model_id: str = DEFAULT_MODEL) -> bytes:
    """
    Calls ElevenLabs API, returns raw MP3 bytes.
    Raises RuntimeError on failure.
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": VOICE_SETTINGS,
    }).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=payload,
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"ElevenLabs connection error: {exc}") from exc


# ── Audio file management ───────────────────────────────────────────────────────
def _voice_dir() -> Path:
    base = Path(settings.MEDIA_ROOT) / "voice"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _greeting_dir() -> Path:
    d = _voice_dir() / "greetings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _response_dir(call_sid: str) -> Path:
    d = _voice_dir() / "responses" / call_sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def audio_url(relative_path: str) -> str:
    """Build public HTTPS URL for an audio file."""
    base = getattr(settings, "KALEYA_PUBLIC_URL", "https://aikaleya.com")
    return f"{base}/media/{relative_path}"


def generate_greeting(
    text: str,
    salon_id: int,
    language: str,
    business_client=None,
) -> str:
    """
    Generates (and caches) the greeting MP3 for a salon+language pair.
    Returns relative media path like 'voice/greetings/1_en.mp3'.
    Re-generates only if text changes (hash-based cache).
    """
    api_key = settings.KALEYA_ELEVENLABS_API_KEY
    voice_id = _get_voice_id(business_client, language)

    # Cache key based on text content
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
    filename = f"{salon_id}_{language}_{text_hash}.mp3"
    rel_path = f"voice/greetings/{filename}"
    full_path = _greeting_dir() / filename

    if full_path.exists():
        return rel_path  # Already cached

    if not api_key:
        return ""  # No API key configured

    audio_bytes = _elevenlabs_tts(text, voice_id, api_key)
    full_path.write_bytes(audio_bytes)
    return rel_path


def generate_response_audio(
    text: str,
    call_sid: str,
    turn: int,
    language: str,
    business_client=None,
    add_filler: bool = True,
) -> str:
    """
    Generates MP3 for a single conversation turn.
    Returns relative media path like 'voice/responses/{call_sid}/turn_3.mp3'.
    Set add_filler=False for silence/error responses (no "Of course!" prefix).
    """
    api_key = settings.KALEYA_ELEVENLABS_API_KEY
    voice_id = _get_voice_id(business_client, language)

    if not api_key:
        return ""

    # Add humanizer filler (skip for silence/error responses)
    final_text = add_humanizer_filler(text, language) if add_filler else text

    filename = f"turn_{turn}_{int(time.time())}.mp3"
    rel_path = f"voice/responses/{call_sid}/{filename}"
    full_path = _response_dir(call_sid) / filename

    audio_bytes = _elevenlabs_tts(final_text, voice_id, api_key)
    full_path.write_bytes(audio_bytes)
    return rel_path


def cleanup_call_audio(call_sid: str):
    """
    Removes all per-turn audio files for a call once it ends.
    Keeps greetings (they're cached and reusable).
    """
    import shutil
    call_dir = _voice_dir() / "responses" / call_sid
    if call_dir.exists():
        shutil.rmtree(call_dir, ignore_errors=True)


def _get_voice_id(business_client=None, language: str = "en") -> str:
    """
    Returns the ElevenLabs voice ID for a business client + language.
    Priority: salon custom voice → per-language env var → platform default.
    """
    if business_client:
        api_settings = getattr(business_client, "api_settings", None)
        voice_settings = getattr(business_client, "voice_settings", None)
        custom_voice = (
            getattr(api_settings, "voice_id", "") or
            (getattr(voice_settings, "voice_id", "") if voice_settings and getattr(voice_settings, "voice_id", "") != "demo-voice" else "")
        )
        if custom_voice:
            return custom_voice
    # Try per-language voice from settings (ELEVENLABS_VOICE_ID_EN, _SR, etc.)
    by_lang = getattr(settings, "KALEYA_ELEVENLABS_VOICE_BY_LANG", {})
    lang_voice = by_lang.get(language, "") or by_lang.get(language.split("-")[0], "")
    if lang_voice:
        return lang_voice
    return settings.KALEYA_ELEVENLABS_VOICE_ID or DEFAULT_VOICE_ID
