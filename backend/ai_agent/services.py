import json
from datetime import date

from django.core.serializers.json import DjangoJSONEncoder

from ai_agent.models import AIIntent, AIToolRun
from ai_agent.providers import ProviderError, generate_anthropic_plan, generate_anthropic_reply, synthesize_elevenlabs_speech
from ai_agent.tools import (
    book_appointment_tool,
    cancel_appointment_tool,
    check_availability_tool,
    reschedule_appointment_tool,
)
from staff_services.models import Service, StaffMember


INTENT_KEYWORDS = {
    "reschedule_appointment": ("pomeri", "promeni", "reschedule", "move", "cambiar", "deplacer", "sposta", "verschieb"),
    "cancel_appointment": ("otkazi", "otkaži", "cancel", "cancela", "annuler", "annulla", "absagen", "stornieren"),
    "check_availability": ("slobodno", "available", "free", "disponible", "livre", "libero", "frei"),
    "support_handoff": ("covek", "čovek", "operater", "support", "human", "agent", "mensch"),
    "book_appointment": ("zakazi", "zakaži", "termin", "appointment", "book", "reserva", "reserver", "prenota", "buchen"),
}

VALID_INTENTS = set(INTENT_KEYWORDS.keys()) | {"business_info", "unknown"}

PLAN_PAYLOAD_KEYS = (
    "customer_name",
    "phone",
    "email",
    "appointment_id",
    "customer_id",
    "service_id",
    "service_hint",
    "staff_member_id",
    "staff_hint",
    "date",
    "time",
    "duration_minutes",
    "title",
)


def json_safe(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def detect_intent(text):
    normalized = (text or "").strip().lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent, 0.82
    return "unknown", 0.25


def clean_empty_values(payload):
    cleaned = {}
    for key, value in (payload or {}).items():
        if value in ("", None, [], {}):
            continue
        cleaned[key] = value
    return cleaned


def safe_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def build_planner_context(business_client):
    services = list(
        Service.objects.filter(business_client=business_client, is_active=True)
        .order_by("category", "name")
        .values("id", "name", "category", "duration_minutes", "price", "currency")[:30]
    )
    staff_members = list(
        StaffMember.objects.filter(business_client=business_client, is_active=True)
        .order_by("full_name")
        .values("id", "full_name", "role_title")[:30]
    )
    return {
        "today": date.today().isoformat(),
        "business": {
            "id": business_client.id,
            "name": business_client.public_name or business_client.name,
            "language": business_client.interface_language or business_client.language or "en",
            "timezone": business_client.timezone,
            "work_start": business_client.work_start.strftime("%H:%M"),
            "work_end": business_client.work_end.strftime("%H:%M"),
            "slot_interval_minutes": business_client.slot_interval_minutes,
        },
        "services": services,
        "staff_members": staff_members,
    }


def normalize_ai_plan(plan):
    if not isinstance(plan, dict):
        return {}

    normalized = {}
    for key in PLAN_PAYLOAD_KEYS:
        value = plan.get(key)
        if value in ("", None, [], {}):
            continue
        if key in {"appointment_id", "customer_id", "service_id", "staff_member_id", "duration_minutes"}:
            try:
                normalized[key] = int(value)
            except (TypeError, ValueError):
                continue
        else:
            normalized[key] = value
    return normalized


def merge_payloads(ai_payload, explicit_payload):
    merged = clean_empty_values(ai_payload)
    merged.update(clean_empty_values(explicit_payload))
    return merged


def build_text_response(business_client, intent, tool_output):
    language = business_client.interface_language or business_client.language or "en"

    if intent == "check_availability":
        count = tool_output.get("free_count", 0)
        suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
        if language == "sr":
            return f"Ima {count} slobodnih termina. Predlog: {suggestions}." if suggestions else f"Ima {count} slobodnih termina."
        if language == "de":
            return f"Es gibt {count} freie Termine. Vorschlag: {suggestions}." if suggestions else f"Es gibt {count} freie Termine."
        return f"There are {count} available slots today."

    if intent == "book_appointment":
        status = tool_output.get("status")
        if status == "booked":
            if language == "sr":
                return f"Termin je zakazan za {tool_output.get('date')} u {tool_output.get('time')}."
            if language == "de":
                return f"Der Termin ist fuer {tool_output.get('date')} um {tool_output.get('time')} gebucht."
            return f"The appointment is booked for {tool_output.get('date')} at {tool_output.get('time')}."
        if status == "needs_time":
            suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
            if language == "sr":
                return f"Mogu da ponudim ove slobodne termine: {suggestions}. Koji zelite?"
            if language == "de":
                return f"Ich kann diese freien Termine anbieten: {suggestions}. Welchen moechten Sie?"
            return f"I can offer these available slots: {suggestions}. Which one works for you?"
        if status == "time_unavailable":
            suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
            if language == "sr":
                return f"Taj termin nije slobodan. Slobodni predlozi su: {suggestions}."
            if language == "de":
                return f"Dieser Termin ist nicht frei. Verfuegbare Vorschlaege: {suggestions}."
            return f"That slot is not available. Available suggestions: {suggestions}."

    if intent == "cancel_appointment":
        if tool_output.get("status") == "cancelled":
            if language == "sr":
                return "Termin je otkazan i slot je oslobodjen."
            if language == "de":
                return "Der Termin wurde abgesagt und der Slot ist wieder frei."
            return "The appointment has been cancelled and the slot is now free."
        if language == "sr":
            return "Treba mi ime, telefon ili tacan termin da bih otkazala pravi termin."
        if language == "de":
            return "Ich brauche Name, Telefon oder den genauen Termin, um den richtigen Termin abzusagen."
        return "I need a name, phone number or exact appointment to cancel the right slot."

    if intent == "reschedule_appointment":
        if tool_output.get("status") == "rescheduled":
            if language == "sr":
                return f"Termin je pomeren na {tool_output.get('date')} u {tool_output.get('time')}."
            if language == "de":
                return f"Der Termin wurde auf {tool_output.get('date')} um {tool_output.get('time')} verschoben."
            return f"The appointment has been moved to {tool_output.get('date')} at {tool_output.get('time')}."
        if language == "sr":
            return "Mogu da pomerim termin, ali treba mi novi datum i vreme."
        if language == "de":
            return "Ich kann den Termin verschieben, brauche aber neues Datum und Uhrzeit."
        return "I can reschedule it, but I need the new date and time."

    if intent == "support_handoff":
        if language == "sr":
            return "Razumem. Prebacujem zahtev support timu."
        return "I understand. I am handing this over to support."

    if intent == "business_info":
        services = list(Service.objects.filter(business_client=business_client, is_active=True).order_by("name")[:5])
        service_names = ", ".join(service.name for service in services)
        if language == "sr":
            return (
                f"Radno vreme je od {business_client.work_start.strftime('%H:%M')} do {business_client.work_end.strftime('%H:%M')}. "
                f"Usluge: {service_names}."
            ).strip()
        if language == "de":
            return (
                f"Die Arbeitszeit ist von {business_client.work_start.strftime('%H:%M')} bis {business_client.work_end.strftime('%H:%M')}. "
                f"Leistungen: {service_names}."
            ).strip()
        return (
            f"Working hours are {business_client.work_start.strftime('%H:%M')} to {business_client.work_end.strftime('%H:%M')}. "
            f"Services: {service_names}."
        ).strip()

    if language == "sr":
        return "Razumem zahtev. Sledeci korak je provera kalendara i potvrda termina."
    return "I understand the request. The next step is checking the calendar and confirming the appointment."


def build_system_prompt(business_client):
    language = business_client.interface_language or business_client.language or "en"
    return (
        "Ti si Kaleya, profesionalna AI sekretarica za zakazivanje termina. "
        "Odgovaraj kratko, jasno i ljubazno. "
        "Ne izmisljaj termine. Tool output je jedini izvor istine za kalendar. "
        "Ako tool output sadrzi free_count, date ili suggested_slots, ne smes reci da ne vidis kalendar ili da nemas datum. "
        "Ako safe_deterministic_response postoji u kontekstu, koristi ga kao proverenu osnovu i samo ga prirodnije formuliši. "
        "Ne koristi emoji. "
        "Ako korisnik trazi nesto sto ne mozes da potvrdis kroz tool output, reci da ces proveriti ili prebaciti supportu. "
        f"Jezik odgovora mora biti: {language}."
    )


def handle_inbound_text(
    business_client,
    text,
    conversation=None,
    customer=None,
    channel="web",
    payload=None,
    use_ai=True,
    include_voice=False,
):
    payload = payload or {}
    planner_raw_response = {"engine": "keyword-fallback"}
    planner_payload = {}
    intent_name, confidence = detect_intent(text)

    if use_ai:
        try:
            planner = generate_anthropic_plan(
                business_client,
                text,
                context=build_planner_context(business_client),
            )
            planned_intent = (planner.get("intent") or "").strip()
            if planned_intent in VALID_INTENTS:
                intent_name = planned_intent
                confidence = safe_float(planner.get("confidence"), 0.86)
            planner_payload = normalize_ai_plan(planner)
            planner_raw_response = {"engine": "anthropic-planner", "plan": planner}
        except ProviderError as exc:
            planner_raw_response = {"engine": "keyword-fallback", "planner_error": str(exc)}

    payload = merge_payloads(planner_payload, payload)
    intent = AIIntent.objects.create(
        business_client=business_client,
        conversation=conversation,
        customer=customer,
        intent=intent_name,
        confidence=confidence,
        input_text=text or "",
        language=business_client.interface_language or business_client.language or "en",
        raw_response=planner_raw_response,
    )

    tool_output = {}
    tool_name = "none"
    status = "skipped"

    if intent_name == "check_availability":
        tool_name = "check_availability"
        tool_output = check_availability_tool(business_client, text, payload)
        status = "success"
    elif intent_name == "book_appointment":
        tool_name = "book_appointment"
        tool_output = book_appointment_tool(business_client, text, customer=customer, channel=channel, payload=payload)
        status = "success" if tool_output.get("status") in {"booked", "needs_time", "time_unavailable"} else "failed"
    elif intent_name == "cancel_appointment":
        tool_name = "cancel_appointment"
        tool_output = cancel_appointment_tool(business_client, text, customer=customer, payload=payload)
        status = "success" if tool_output.get("status") == "cancelled" else "planned"
    elif intent_name == "reschedule_appointment":
        tool_name = "reschedule_appointment"
        tool_output = reschedule_appointment_tool(business_client, text, customer=customer, channel=channel, payload=payload)
        status = "success" if tool_output.get("status") == "rescheduled" else "planned"
    elif intent_name == "support_handoff":
        tool_name = "handoff_to_support"
        tool_output = {"handoff": True, "channel": channel}
        status = "success"
    elif intent_name == "business_info":
        tool_name = "business_info"
        tool_output = {
            "business_name": business_client.public_name or business_client.name,
            "work_start": business_client.work_start.strftime("%H:%M"),
            "work_end": business_client.work_end.strftime("%H:%M"),
            "slot_interval_minutes": business_client.slot_interval_minutes,
        }
        status = "success"

    tool_run = AIToolRun.objects.create(
        business_client=business_client,
        intent=intent,
        tool_name=tool_name,
        status=status,
        input_payload=json_safe({"text": text, "channel": channel, "payload": payload}),
        output_payload=json_safe(tool_output),
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
                    "safe_deterministic_response": response_text,
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
