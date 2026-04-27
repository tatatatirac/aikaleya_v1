from datetime import date as date_cls

from ai_agent.models import AIIntent, AIToolRun
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


def handle_inbound_text(business_client, text, conversation=None, customer=None, channel="web"):
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

    AIToolRun.objects.create(
        business_client=business_client,
        intent=intent,
        tool_name=tool_name,
        status=status,
        input_payload={"text": text, "channel": channel},
        output_payload=tool_output,
    )

    return {
        "intent": intent.intent,
        "confidence": float(intent.confidence),
        "response_text": build_text_response(business_client, intent.intent, tool_output),
        "tool_output": tool_output,
    }
