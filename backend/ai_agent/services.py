from datetime import date as date_cls

from ai_agent.models import AIIntent, AIToolRun
from ai_agent.providers import ProviderError, generate_anthropic_reply, synthesize_elevenlabs_speech
from appointments.services import availability_for_date


INTENT_KEYWORDS = {
    "book_appointment": ("zakazi", "termin", "appointment", "book", "reserva", "reserver", "prenota"),
    "reschedule_appointment": ("pomeri", "promeni", "reschedule", "move", "cambiar", "deplacer", "sposta"),
    "cancel_appointment": ("otkazi", "cancel", "cancela", "annuler", "annulla"),
    "check_availability": ("slobodno", "available", "free", "disponible", "livre", "libero"),
    "support_handoff": ("covek", "operater", "support", "human", "agent"),
}


def detect_intent(text):
    normalized = (text or "").strip().lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent, 0.82
    return "unknown", 0.25


def build_text_response(business_client, intent, tool_output):
    language = business_client.interface_language or business_client.language or "en"

    if intent == "check_availability":
        count = tool_output.get("free_count", 0)
        if language == "sr":
            return f"Danas ima {count} slobodnih termina."
        return f"There are {count} available slots today."

    if intent == "support_handoff":
        if language == "sr":
            return "Razumem. Prebacujem zahtev support timu."
        return "I understand. I am handing this over to support."

    if language == "sr":
        return "Razumem zahtev. Sledeci korak je provera kalendara i potvrda termina."
    return "I understand the request. The next step is checking the calendar and confirming the appointment."


def build_system_prompt(business_client):
    language = business_client.interface_language or business_client.language or "en"
    return (
        "Ti si Kaleya, profesionalna AI sekretarica za zakazivanje termina. "
        "Odgovaraj kratko, jasno i ljubazno. "
        "Ne izmisljaj termine. Ako dobijes podatke o slobodnim slotovima, koristi samo te podatke. "
        "Ako korisnik trazi nesto sto ne mozes da potvrdis, reci da ces proveriti ili prebaciti supportu. "
        f"Jezik odgovora mora biti: {language}."
    )


def handle_inbound_text(
    business_client,
    text,
    conversation=None,
    customer=None,
    channel="web",
    use_ai=True,
    include_voice=False,
):
    intent_name, confidence = detect_intent(text)
    intent = AIIntent.objects.create(
        business_client=business_client,
        conversation=conversation,
        customer=customer,
        intent=intent_name,
        confidence=confidence,
        input_text=text or "",
        language=business_client.interface_language or business_client.language or "en",
        raw_response={"engine": "keyword-fallback"},
    )

    tool_output = {}
    tool_name = "none"
    status = "skipped"

    if intent_name == "check_availability":
        tool_name = "check_availability"
        tool_output = availability_for_date(business_client, date_cls.today())
        status = "success"
    elif intent_name == "support_handoff":
        tool_name = "handoff_to_support"
        tool_output = {"handoff": True, "channel": channel}
        status = "success"

    tool_run = AIToolRun.objects.create(
        business_client=business_client,
        intent=intent,
        tool_name=tool_name,
        status=status,
        input_payload={"text": text, "channel": channel},
        output_payload=tool_output,
    )

    response_text = build_text_response(business_client, intent.intent, tool_output)
    ai_provider_used = "fallback"

    if use_ai:
        try:
            response_text = generate_anthropic_reply(
                business_client,
                text,
                build_system_prompt(business_client),
                context={
                    "business": {
                        "name": business_client.public_name or business_client.name,
                        "work_start": business_client.work_start.strftime("%H:%M"),
                        "work_end": business_client.work_end.strftime("%H:%M"),
                        "slot_interval_minutes": business_client.slot_interval_minutes,
                    },
                    "detected_intent": intent.intent,
                    "tool_output": tool_output,
                },
            ) or response_text
            ai_provider_used = "anthropic"
        except ProviderError as exc:
            tool_run.status = "failed"
            tool_run.error = str(exc)
            tool_run.save(update_fields=["status", "error"])

    voice = None
    if include_voice:
        try:
            voice = synthesize_elevenlabs_speech(business_client, response_text)
        except ProviderError as exc:
            voice = {"error": str(exc)}

    return {
        "intent": intent.intent,
        "confidence": float(intent.confidence),
        "response_text": response_text,
        "ai_provider": ai_provider_used,
        "voice": voice,
        "tool_output": tool_output,
    }
