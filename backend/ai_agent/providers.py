import hashlib
import json
from pathlib import Path
from urllib import error, parse, request

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


class ProviderError(Exception):
    pass


def _extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProviderError("AI planner nije vratio JSON odgovor.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderError(f"AI planner JSON nije validan: {exc}") from exc


def _post_json(url, payload, headers, timeout=45):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"Provider HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise ProviderError(f"Provider connection error: {exc}") from exc


def _post_binary(url, payload, headers, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderError(f"Provider HTTP {exc.code}: {body}") from exc
    except error.URLError as exc:
        raise ProviderError(f"Provider connection error: {exc}") from exc


def get_client_ai_config(business_client):
    api_settings = getattr(business_client, "api_settings", None)
    provider = (getattr(api_settings, "ai_provider", "") or settings.KALEYA_AI_PROVIDER or "anthropic").lower()

    if provider == "anthropic":
        return {
            "provider": "anthropic",
            "api_key": getattr(api_settings, "ai_api_key", "") or settings.KALEYA_ANTHROPIC_API_KEY,
            "model": getattr(api_settings, "ai_model", "") or settings.KALEYA_ANTHROPIC_MODEL,
        }

    return {
        "provider": provider,
        "api_key": getattr(api_settings, "ai_api_key", ""),
        "model": getattr(api_settings, "ai_model", ""),
    }


def get_client_voice_config(business_client):
    api_settings = getattr(business_client, "api_settings", None)
    voice_settings = getattr(business_client, "voice_settings", None)
    voice_id = getattr(api_settings, "voice_id", "") or settings.KALEYA_ELEVENLABS_VOICE_ID
    if not voice_id and voice_settings and getattr(voice_settings, "voice_id", "") != "demo-voice":
        voice_id = voice_settings.voice_id

    return {
        "provider": "elevenlabs",
        "api_key": getattr(api_settings, "voice_api_key", "") or settings.KALEYA_ELEVENLABS_API_KEY,
        "voice_id": voice_id,
        "model_id": getattr(api_settings, "voice_model", "") or "eleven_multilingual_v2",
        "stability": float(getattr(voice_settings, "stability", 0.5) or 0.5),
        "similarity_boost": float(getattr(voice_settings, "similarity_boost", 0.75) or 0.75),
    }


def generate_anthropic_reply(business_client, user_text, system_prompt, context=None):
    config = get_client_ai_config(business_client)
    if config["provider"] != "anthropic":
        raise ProviderError(f"Nepodrzan AI provider: {config['provider']}")
    if not config["api_key"]:
        raise ProviderError("ANTHROPIC_API_KEY nije podesen.")

    context_text = json.dumps(context or {}, ensure_ascii=False)
    payload = {
        "model": config["model"],
        "max_tokens": 450,
        "temperature": 0.3,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Kontekst sistema:\n"
                    f"{context_text}\n\n"
                    "Poruka korisnika:\n"
                    f"{user_text}"
                ),
            }
        ],
    }
    response = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "Content-Type": "application/json",
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
        },
    )
    content = response.get("content") or []
    text_blocks = [item.get("text", "") for item in content if item.get("type") == "text"]
    return "\n".join(block for block in text_blocks if block).strip()


def generate_anthropic_plan(business_client, user_text, context=None):
    config = get_client_ai_config(business_client)
    if config["provider"] != "anthropic":
        raise ProviderError(f"Nepodrzan AI provider: {config['provider']}")
    if not config["api_key"]:
        raise ProviderError("ANTHROPIC_API_KEY nije podesen.")

    context_text = json.dumps(context or {}, ensure_ascii=False, default=str)
    system_prompt = (
        "You are Kaleya's scheduling planner. "
        "Your only job is to convert the user's message into one valid JSON object. "
        "Do not answer conversationally. Do not use Markdown. "
        "Allowed intents: book_appointment, reschedule_appointment, cancel_appointment, "
        "check_availability, business_info, support_handoff, unknown. "
        "Use null when a value is missing. Dates must be YYYY-MM-DD. Times must be HH:MM in 24h format. "
        "If the user asks for the first available slot, leave staff_member_id null and set staff_hint to null. "
        "If the user mentions a service or employee by name, put that text in service_hint or staff_hint. "
        "Return keys: intent, confidence, date, time, duration_minutes, customer_name, phone, email, "
        "appointment_id, service_id, service_hint, staff_member_id, staff_hint, title, needs_human_support."
    )
    payload = {
        "model": config["model"],
        "max_tokens": 700,
        "temperature": 0,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Business context:\n"
                    f"{context_text}\n\n"
                    "User message:\n"
                    f"{user_text}\n\n"
                    "Return only JSON."
                ),
            }
        ],
    }
    response = _post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        {
            "Content-Type": "application/json",
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
        },
    )
    content = response.get("content") or []
    text_blocks = [item.get("text", "") for item in content if item.get("type") == "text"]
    return _extract_json_object("\n".join(text_blocks))


def synthesize_elevenlabs_speech(business_client, text):
    config = get_client_voice_config(business_client)
    if not config["api_key"]:
        raise ProviderError("ELEVENLABS_API_KEY nije podesen.")
    if not config["voice_id"]:
        raise ProviderError("ELEVENLABS_VOICE_ID nije podesen.")
    if not text.strip():
        raise ProviderError("Tekst za glas je prazan.")

    digest_source = f"{config['voice_id']}|{config['model_id']}|{text[:2500]}"
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:32]
    filename = f"voice/tts/{business_client.id}/kaleya-{digest}.mp3"
    if default_storage.exists(filename):
        return {
            "audio_path": filename,
            "audio_url": settings.MEDIA_URL + Path(filename).as_posix(),
            "bytes": default_storage.size(filename),
            "cached": True,
        }

    query = parse.urlencode({"output_format": "mp3_44100_128"})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{config['voice_id']}?{query}"
    payload = {
        "text": text[:2500],
        "model_id": config["model_id"],
        "voice_settings": {
            "stability": config["stability"],
            "similarity_boost": config["similarity_boost"],
        },
    }
    audio_bytes = _post_binary(
        url,
        payload,
        {
            "Content-Type": "application/json",
            "xi-api-key": config["api_key"],
        },
    )

    saved_path = default_storage.save(filename, ContentFile(audio_bytes))
    return {
        "audio_path": saved_path,
        "audio_url": settings.MEDIA_URL + Path(saved_path).as_posix(),
        "bytes": len(audio_bytes),
        "cached": False,
    }
