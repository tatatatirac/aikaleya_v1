import json
import re
import unicodedata
from datetime import date

from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

from ai_agent.models import AIIntent, AIToolRun, CustomerMemory
from ai_agent.providers import ProviderError, generate_anthropic_plan, generate_anthropic_reply, synthesize_elevenlabs_speech
from ai_agent.tools import (
    book_appointment_tool,
    cancel_appointment_tool,
    check_availability_tool,
    client_local_today,
    infer_payload_from_text,
    parse_requested_date,
    parse_requested_time,
    reschedule_appointment_tool,
    text_has_parseable_date,
)
from accounts.permissions import user_role
from audit_log.services import write_audit_log
from appointments.models import Appointment, Customer
from clients.models import BusinessKnowledgeEntry, ClientApiSettings
from communications.models import Conversation, Message
from notifications.services import queue_notification_jobs_for_event
from staff_services.models import Service, StaffMember
from support.models import SupportTicket


INTENT_KEYWORDS = {
    "reschedule_appointment": ("pomeri", "promeni", "reschedule", "move", "cambiar", "deplacer", "sposta", "verschieb"),
    "cancel_appointment": ("otkazi", "otkaži", "cancel", "cancela", "annuler", "annulla", "absagen", "stornieren"),
    "check_availability": ("slobodno", "available", "free", "disponible", "livre", "libero", "frei"),
    "support_handoff": ("covek", "čovek", "operater", "support", "human", "agent", "mensch"),
    "book_appointment": ("zakazi", "zakaži", "termin", "appointment", "book", "reserva", "reserver", "prenota", "buchen"),
}

VALID_INTENTS = set(INTENT_KEYWORDS.keys()) | {"business_info", "unknown"}
INTENT_KEYWORDS.update(
    {
        "cancel_appointment": ("otkazi", "otkaz", "cancel", "cancela", "annuler", "annulla", "absagen", "stornieren", "отмен"),
        "business_info": ("cena", "price", "cost", "radno vreme", "working hours", "address", "adresa", "usluge", "services"),
        "support_handoff": ("covek", "operater", "support", "human", "agent", "mensch", "zalba", "problem", "complaint"),
        "reschedule_appointment": ("pomeri", "promeni", "reschedule", "move", "cambiar", "deplacer", "déplacer", "sposta", "spostare", "verschieb", "remarcar", "alterar", "перенес"),
        "book_appointment": ("zakazi", "zakaz", "termin", "appointment", "book", "reserva", "reserver", "rendez-vous", "prenota", "appuntamento", "buchen", "marcar", "agendar", "consulta", "запис"),
    }
)
VALID_INTENTS = set(INTENT_KEYWORDS.keys()) | {"unknown"}
LOW_CONFIDENCE_THRESHOLD = 0.45
MAX_UNKNOWN_BEFORE_HANDOFF = 2
AVAILABILITY_HINTS = (
    "slobodnih termina",
    "slobodni termini",
    "slobodne termine",
    "slobodan termin",
    "slobodno vreme",
    "слободних термина",
    "слободни термини",
    "слободан термин",
    "ima slobodnih",
    "ima li slobod",
    "da li ima slobod",
    "има слободних",
    "да ли има слобод",
    "proveri slobod",
    "provera slobod",
    "free slots",
    "available slots",
    "available appointments",
    "citas disponibles",
    "cita disponible",
    "horarios disponibles",
    "horarios livres",
    "disponibil",
    "disponible",
    "disponivel",
    "livre",
    "libero",
    "frei",
    "freie termine",
    "свобод",
)
BOOKING_ACTION_HINTS = (
    "zakazi",
    "zakaži",
    "zakazivanje",
    "rezervisi",
    "rezerviši",
    "book",
    "reserve",
    "schedule",
)

DATE_HINT_PATTERN = re.compile(r"\b(20\d{2}-\d{2}-\d{2}|\d{1,2}[.\-/]\d{1,2}[.\-/]20\d{2})\b")
DATE_HINT_WORDS = (
    "danas",
    "sutra",
    "today",
    "tomorrow",
    "hoy",
    "manana",
    "mañana",
    "hoje",
    "amanha",
    "amanhã",
    "demain",
    "oggi",
    "morgen",
    "heute",
)

AVAILABILITY_RESPONSE_TEMPLATES = {
    "en": (
        "There are {count} available slots. Suggestions: {suggestions}.",
        "There are {count} available slots.",
    ),
    "sr": (
        "Ima {count} slobodnih termina. Predlog: {suggestions}.",
        "Ima {count} slobodnih termina.",
    ),
    "es": (
        "Hay {count} turnos disponibles. Sugerencia: {suggestions}.",
        "Hay {count} turnos disponibles.",
    ),
    "pt": (
        "Há {count} horários disponíveis. Sugestão: {suggestions}.",
        "Há {count} horários disponíveis.",
    ),
    "ru": (
        "Есть {count} свободных слотов. Вариант: {suggestions}.",
        "Есть {count} свободных слотов.",
    ),
    "fr": (
        "Il y a {count} créneaux disponibles. Proposition: {suggestions}.",
        "Il y a {count} créneaux disponibles.",
    ),
    "it": (
        "Ci sono {count} slot disponibili. Proposta: {suggestions}.",
        "Ci sono {count} slot disponibili.",
    ),
    "de": (
        "Es gibt {count} freie Termine. Vorschlag: {suggestions}.",
        "Es gibt {count} freie Termine.",
    ),
}

BOOKING_RESPONSE_TEMPLATES = {
    "booked": {
        "en": "The appointment is booked for {date} at {time}.",
        "sr": "Termin je zakazan za {date} u {time}.",
        "es": "La cita esta reservada para {date} a las {time}.",
        "pt": "O agendamento esta marcado para {date} as {time}.",
        "ru": "Запись назначена на {date} в {time}.",
        "fr": "Le rendez-vous est reserve pour le {date} a {time}.",
        "it": "L'appuntamento e prenotato per il {date} alle {time}.",
        "de": "Der Termin ist fuer {date} um {time} gebucht.",
    },
    "needs_time": {
        "en": "I can offer these available slots: {suggestions}. Which one works for you?",
        "sr": "Mogu da ponudim ove slobodne termine: {suggestions}. Koji zelite?",
        "es": "Puedo ofrecer estos horarios disponibles: {suggestions}. Cual le viene bien?",
        "pt": "Posso oferecer estes horarios disponiveis: {suggestions}. Qual prefere?",
        "ru": "Могу предложить эти свободные слоты: {suggestions}. Какой вам подходит?",
        "fr": "Je peux proposer ces creneaux disponibles: {suggestions}. Lequel vous convient?",
        "it": "Posso proporre questi slot disponibili: {suggestions}. Quale preferisce?",
        "de": "Ich kann diese freien Termine anbieten: {suggestions}. Welchen moechten Sie?",
    },
    "time_unavailable": {
        "en": "That slot is not available. Available suggestions: {suggestions}.",
        "sr": "Taj termin nije slobodan. Slobodni predlozi su: {suggestions}.",
        "es": "Ese horario no esta disponible. Opciones disponibles: {suggestions}.",
        "pt": "Esse horario nao esta disponivel. Sugestoes disponiveis: {suggestions}.",
        "ru": "Этот слот недоступен. Доступные варианты: {suggestions}.",
        "fr": "Ce creneau n'est pas disponible. Propositions disponibles: {suggestions}.",
        "it": "Quello slot non e disponibile. Proposte disponibili: {suggestions}.",
        "de": "Dieser Termin ist nicht frei. Verfuegbare Vorschlaege: {suggestions}.",
    },
}

CANCEL_RESPONSE_TEMPLATES = {
    "cancelled": {
        "en": "The appointment has been cancelled and the slot is now free.",
        "sr": "Termin je otkazan i slot je oslobodjen.",
        "es": "La cita se ha cancelado y el horario queda libre.",
        "pt": "O agendamento foi cancelado e o horario ficou livre.",
        "ru": "Запись отменена, слот снова свободен.",
        "fr": "Le rendez-vous a ete annule et le creneau est libere.",
        "it": "L'appuntamento e stato annullato e lo slot e libero.",
        "de": "Der Termin wurde abgesagt und der Slot ist wieder frei.",
    },
    "target_missing": {
        "en": "I need a name, phone number or exact appointment to cancel the right slot.",
        "sr": "Treba mi ime, telefon ili tacan termin da bih otkazala pravi termin.",
        "es": "Necesito nombre, telefono o cita exacta para cancelar el horario correcto.",
        "pt": "Preciso do nome, telefone ou agendamento exato para cancelar o horario correto.",
        "ru": "Мне нужно имя, телефон или точная запись, чтобы отменить правильный слот.",
        "fr": "J'ai besoin du nom, du telephone ou du rendez-vous exact pour annuler le bon creneau.",
        "it": "Mi serve nome, telefono o appuntamento esatto per annullare lo slot corretto.",
        "de": "Ich brauche Name, Telefon oder den genauen Termin, um den richtigen Termin abzusagen.",
    },
}

RESCHEDULE_RESPONSE_TEMPLATES = {
    "rescheduled": {
        "en": "The appointment has been moved to {date} at {time}.",
        "sr": "Termin je pomeren na {date} u {time}.",
        "es": "La cita se ha movido a {date} a las {time}.",
        "pt": "O agendamento foi remarcado para {date} as {time}.",
        "ru": "Запись перенесена на {date} в {time}.",
        "fr": "Le rendez-vous a ete deplace au {date} a {time}.",
        "it": "L'appuntamento e stato spostato al {date} alle {time}.",
        "de": "Der Termin wurde auf {date} um {time} verschoben.",
    },
    "missing_new_time": {
        "en": "I can reschedule it, but I need the new date and time.",
        "sr": "Mogu da pomerim termin, ali treba mi novi datum i vreme.",
        "es": "Puedo cambiar la cita, pero necesito la nueva fecha y hora.",
        "pt": "Posso remarcar, mas preciso da nova data e hora.",
        "ru": "Я могу перенести запись, но мне нужны новая дата и время.",
        "fr": "Je peux deplacer le rendez-vous, mais il me faut la nouvelle date et l'heure.",
        "it": "Posso spostare l'appuntamento, ma mi servono nuova data e ora.",
        "de": "Ich kann den Termin verschieben, brauche aber neues Datum und Uhrzeit.",
    },
    "needs_time": {
        "en": "I can move it to {date}. Available slots: {suggestions}. Which one works for you?",
        "sr": "Mogu da pomerim termin na {date}. Slobodni termini: {suggestions}. Koji zelite?",
        "es": "Puedo mover la cita a {date}. Horarios disponibles: {suggestions}. Cual le viene bien?",
        "pt": "Posso remarcar para {date}. Horarios disponiveis: {suggestions}. Qual prefere?",
        "ru": "Могу перенести запись на {date}. Доступные слоты: {suggestions}. Какой вам подходит?",
        "fr": "Je peux deplacer le rendez-vous au {date}. Creneaux disponibles: {suggestions}. Lequel vous convient?",
        "it": "Posso spostare l'appuntamento al {date}. Slot disponibili: {suggestions}. Quale preferisce?",
        "de": "Ich kann den Termin auf {date} verschieben. Freie Termine: {suggestions}. Welcher passt?",
    },
}

APPOINTMENT_TARGET_STOP_WORDS = {
    "please",
    "cancel",
    "appointment",
    "booking",
    "reschedule",
    "move",
    "otkazi",
    "otkaz",
    "pomeri",
    "promeni",
    "termin",
    "zakazivanje",
    "cita",
    "reserva",
    "annuler",
    "rendez",
    "termin",
    "absagen",
    "buchen",
    "today",
    "tomorrow",
    "danas",
    "sutra",
}

LANGUAGE_HINTS = (
    ("sr", ("zakaz", "termin", "sutra", "danas", "otkaz", "pomeri", "usluga", "radno vreme", "слобод", "термин", "данас", "сутра")),
    ("en", ("appointment", "book", "cancel", "reschedule", "available", "today", "tomorrow", "free slots")),
    ("es", ("cita", "reserva", "cancelar", "disponible", "manana", "mañana", "hoy", "servicio")),
    ("pt", ("marcar", "consulta", "cancelar", "disponivel", "disponível", "amanha", "amanhã", "hoje", "horario", "horário", "servico", "serviço")),
    ("fr", ("rendez", "annuler", "disponible", "demain", "aujourd", "creneau", "créneau")),
    ("it", ("appuntament", "prenota", "annulla", "disponibile", "domani", "oggi")),
    ("de", ("termin", "buchen", "absagen", "frei", "morgen", "heute")),
    ("ru", ("запис", "сегодня", "завтра", "отмен", "свобод")),
)

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
    "reason",
    "cancelled_reason",
)

WORKFLOW_STEPS = (
    "preprocess",
    "understand",
    "route",
    "collect_missing_data",
    "execute_backend_tool",
    "respond",
    "audit",
)
RESUMABLE_INTENTS = {
    "book_appointment",
    "reschedule_appointment",
    "cancel_appointment",
    "check_availability",
}
AMBIGUOUS_COMPLETED_FOLLOWUP_INTENTS = {"unknown", "book_appointment", "check_availability"}


def json_safe(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def normalize_intent_text(value):
    normalized = unicodedata.normalize("NFKD", str(value or "")).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", normalized).strip()


def contains_normalized_hint(text, hints):
    normalized = normalize_intent_text(text)
    return any(normalize_intent_text(hint) in normalized for hint in hints)


def localized_availability_response(language, count, suggestions):
    templates = AVAILABILITY_RESPONSE_TEMPLATES.get(language) or AVAILABILITY_RESPONSE_TEMPLATES["en"]
    template = templates[0] if suggestions else templates[1]
    return template.format(count=count, suggestions=suggestions)


def localized_status_response(templates_by_status, status, language, **context):
    templates = templates_by_status.get(status) or {}
    template = templates.get(language) or templates.get("en") or ""
    return template.format(**context)


def detect_intent(text):
    normalized = normalize_intent_text(text)
    has_availability_hint = contains_normalized_hint(normalized, AVAILABILITY_HINTS)
    has_booking_action = contains_normalized_hint(normalized, BOOKING_ACTION_HINTS)
    if has_availability_hint and not has_booking_action:
        return "check_availability", 0.88
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(normalize_intent_text(keyword) in normalized for keyword in keywords):
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


def text_has_date_hint(text):
    normalized = normalize_intent_text(text)
    return bool(
        DATE_HINT_PATTERN.search(normalized)
        or text_has_parseable_date(text)
        or any(normalize_intent_text(word) in normalized for word in DATE_HINT_WORDS)
    )


def detect_message_language(text, fallback="en"):
    normalized = normalize_intent_text(text)
    if not normalized:
        return fallback or "en"

    best_language = fallback or "en"
    best_score = 0
    for language, hints in LANGUAGE_HINTS:
        score = sum(1 for hint in hints if normalize_intent_text(hint) in normalized)
        if score > best_score:
            best_language = language
            best_score = score
    if best_score:
        return best_language
    if re.search(r"[а-яА-Я]", text or ""):
        return "ru"
    return fallback or "en"


def customer_identity_present(customer=None, payload=None):
    payload = payload or {}
    return bool(
        customer
        or payload.get("customer_id")
        or payload.get("phone")
        or payload.get("email")
        or payload.get("customer_name")
    )


def appointment_identity_present(customer=None, payload=None):
    payload = payload or {}
    return bool(
        customer
        or payload.get("appointment_id")
        or payload.get("customer_id")
        or payload.get("phone")
        or payload.get("email")
        or payload.get("customer_name")
    )


def text_has_possible_appointment_target(text):
    tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-zÀ-žА-Яа-я0-9]+", text or "")
        if len(token) >= 3
    ]
    useful_tokens = [token for token in tokens if token not in APPOINTMENT_TARGET_STOP_WORDS]
    return bool(useful_tokens)


def cancel_target_present(text, payload=None, customer=None):
    payload = payload or {}
    if appointment_identity_present(customer=customer, payload=payload):
        return True
    if text_has_possible_appointment_target(text):
        return True
    if (payload.get("date") or text_has_date_hint(text)) and (payload.get("time") or parse_requested_time(text)):
        return True
    return False


def ensure_workflow_conversation(business_client, conversation=None, customer=None, channel="web", external_thread_id="", language="en"):
    if conversation:
        return conversation

    query = Conversation.objects.filter(business_client=business_client, channel=channel)
    if external_thread_id:
        existing = query.filter(external_thread_id=external_thread_id).order_by("-updated_at").first()
        if existing:
            if customer and existing.customer_id != customer.id:
                existing.customer = customer
                existing.save(update_fields=["customer", "updated_at"])
            return existing

    if customer:
        existing = query.filter(customer=customer, status__in=["open", "waiting", "handoff"]).order_by("-updated_at").first()
        if existing:
            return existing

    return Conversation.objects.create(
        business_client=business_client,
        customer=customer,
        channel=channel,
        external_thread_id=external_thread_id or "",
        language=language,
        last_message_at=timezone.now(),
    )


def write_workflow_message(conversation, direction, body, sender_label="", raw_payload=None):
    if not conversation:
        return None
    message = Message.objects.create(
        conversation=conversation,
        direction=direction,
        message_type="text",
        sender_label=sender_label,
        body=body or "",
        raw_payload=raw_payload or {},
    )
    Conversation.objects.filter(id=conversation.id).update(last_message_at=timezone.now())
    return message


def get_conversation_ai_state(conversation):
    if not conversation:
        return {}
    metadata = conversation.metadata or {}
    state = metadata.get("ai_state") or {}
    return state if isinstance(state, dict) else {}


def merge_conversation_payload(conversation, payload):
    state = get_conversation_ai_state(conversation)
    pending_payload = state.get("pending_payload") or {}
    if not isinstance(pending_payload, dict):
        pending_payload = {}
    return merge_payloads(pending_payload, payload)


def build_preprocess_context(business_client, text, customer=None, payload=None, channel="web", language_fallback=""):
    payload = payload or {}
    language = detect_message_language(text, language_fallback or business_client.interface_language or business_client.language or "en")
    requested_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
    requested_time = parse_requested_time(text, payload.get("time"))
    customer_filter = None
    if customer:
        customer_filter = {"customer": customer}
    elif payload.get("phone"):
        customer_filter = {"customer__phone__icontains": payload["phone"]}
    elif payload.get("email"):
        customer_filter = {"customer__email__iexact": payload["email"]}

    total_appointments = 0
    cancelled_appointments = 0
    if customer_filter:
        appointments = business_client.appointments.filter(**customer_filter)
        total_appointments = appointments.count()
        cancelled_appointments = appointments.filter(status="cancelled").count()

    no_show_risk = "low"
    if total_appointments >= 3 and cancelled_appointments / max(total_appointments, 1) >= 0.5:
        no_show_risk = "high"
    elif cancelled_appointments:
        no_show_risk = "medium"

    return json_safe(
        {
            "channel": channel,
            "language": language,
            "customer_identified": customer_identity_present(customer, payload),
            "date_hint_present": bool(payload.get("date") or text_has_date_hint(text)),
            "time_hint_present": bool(payload.get("time") or requested_time),
            "requested_date": requested_date,
            "requested_time": requested_time,
            "no_show_risk": no_show_risk,
            "history": {
                "total_appointments": total_appointments,
                "cancelled_appointments": cancelled_appointments,
            },
            "workflow_steps": WORKFLOW_STEPS,
        }
    )


def service_choice_missing(business_client, payload):
    if payload.get("service_id") or payload.get("service_hint"):
        return False
    return Service.objects.filter(business_client=business_client, is_active=True).exists()


def booking_missing_fields(text, payload, customer=None):
    missing = []
    if not payload.get("date") and not text_has_date_hint(text):
        missing.append("date")
    if not customer_identity_present(customer, payload):
        missing.append("customer_contact")
    return missing


def workflow_missing_fields(business_client, intent_name, text, payload, customer=None):
    if intent_name == "book_appointment":
        missing = booking_missing_fields(text, payload, customer=customer)
        if service_choice_missing(business_client, payload):
            missing.append("service")
        return missing
    if intent_name == "reschedule_appointment":
        missing = []
        if not appointment_identity_present(customer=customer, payload=payload):
            missing.append("appointment_target")
        if not payload.get("date") and not text_has_date_hint(text):
            missing.append("new_date")
        return missing
    if intent_name == "cancel_appointment":
        if not cancel_target_present(text, payload=payload, customer=customer):
            return ["appointment_target"]
        return []
    return []


def service_options_text(business_client, limit=6):
    services = Service.objects.filter(business_client=business_client, is_active=True).order_by("category", "name")[:limit]
    return ", ".join(service.name for service in services)


def customer_memory_service_prompt(customer_memory):
    if not customer_memory:
        return ""
    return customer_memory.get("favorite_service") or customer_memory.get("last_service") or ""


def memory_prioritized_suggestions(tool_output):
    suggestions = list((tool_output or {}).get("suggested_slots", [])[:5])
    customer_memory = (tool_output or {}).get("customer_memory") or {}
    favorite_time = customer_memory.get("favorite_time") or ""
    if favorite_time:
        preferred = [slot for slot in suggestions if str(slot).startswith(favorite_time)]
        remaining = [slot for slot in suggestions if slot not in preferred]
        suggestions = preferred + remaining
    return ", ".join(suggestions[:3])


def service_clarifying_response(business_client, language, customer_memory=None):
    options = service_options_text(business_client)
    memory_service = customer_memory_service_prompt(customer_memory)
    if language == "sr":
        if memory_service:
            return f"Da li zelite opet {memory_service}? Dostupne usluge: {options}." if options else f"Da li zelite opet {memory_service}?"
        return f"Za koju uslugu zelite termin? Dostupne usluge: {options}." if options else "Za koju uslugu zelite termin?"
    if language == "de":
        if memory_service:
            return f"Moechten Sie wieder {memory_service}? Verfuegbare Leistungen: {options}." if options else f"Moechten Sie wieder {memory_service}?"
        return f"Fuer welche Leistung moechten Sie den Termin? Verfuegbare Leistungen: {options}." if options else "Fuer welche Leistung moechten Sie den Termin?"
    if language == "es":
        if memory_service:
            return f"Quiere de nuevo {memory_service}? Servicios disponibles: {options}." if options else f"Quiere de nuevo {memory_service}?"
        return f"Para que servicio quiere la cita? Servicios disponibles: {options}." if options else "Para que servicio quiere la cita?"
    if language == "pt":
        if memory_service:
            return f"Quer novamente {memory_service}? Servicos disponiveis: {options}." if options else f"Quer novamente {memory_service}?"
        return f"Para qual servico quer o agendamento? Servicos disponiveis: {options}." if options else "Para qual servico quer o agendamento?"
    if language == "fr":
        if memory_service:
            return f"Souhaitez-vous a nouveau {memory_service}? Services disponibles: {options}." if options else f"Souhaitez-vous a nouveau {memory_service}?"
        return f"Pour quel service souhaitez-vous le rendez-vous? Services disponibles: {options}." if options else "Pour quel service souhaitez-vous le rendez-vous?"
    if language == "it":
        if memory_service:
            return f"Desidera di nuovo {memory_service}? Servizi disponibili: {options}." if options else f"Desidera di nuovo {memory_service}?"
        return f"Per quale servizio desidera l'appuntamento? Servizi disponibili: {options}." if options else "Per quale servizio desidera l'appuntamento?"
    if language == "ru":
        if memory_service:
            return f"Хотите снова {memory_service}? Доступные услуги: {options}." if options else f"Хотите снова {memory_service}?"
        return f"Для какой услуги нужна запись? Доступные услуги: {options}." if options else "Для какой услуги нужна запись?"
    if memory_service:
        return f"Would you like {memory_service} again? Available services: {options}." if options else f"Would you like {memory_service} again?"
    return f"Which service would you like to book? Available services: {options}." if options else "Which service would you like to book?"


def build_clarifying_response(business_client, intent, missing_fields, tool_output=None):
    tool_output = tool_output or {}
    language = tool_output.get("response_language") or business_client.interface_language or business_client.language or "en"
    missing = set(missing_fields or [])
    suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
    customer_memory = tool_output.get("customer_memory") or {}

    if language == "sr":
        if "date" in missing and "customer_contact" in missing:
            return "Mogu da pomognem. Treba mi datum termina i ime ili telefon klijenta."
        if "date" in missing:
            return "Za koji datum zelite termin?"
        if "customer_contact" in missing:
            return "Treba mi ime ili telefon klijenta da bih mogla bezbedno da zakazem termin."
        if "service" in missing:
            return service_clarifying_response(business_client, language, customer_memory)
        if "appointment_target" in missing:
            return "Treba mi ime, telefon ili tacan termin da bih pronasla rezervaciju."
        if "new_date" in missing and "new_time" in missing:
            return "Na koji datum i u koje vreme zelite da pomerim termin?"
        if "new_date" in missing:
            return "Na koji datum zelite da pomerim termin?"
        if "new_time" in missing:
            return "U koje vreme zelite novi termin?"
        if "intent" in missing:
            return "Mozete li napisati da li zelite zakazivanje, otkazivanje, pomeranje ili proveru termina?"
        if suggestions:
            return f"Mogu da ponudim ove termine: {suggestions}. Koji vam odgovara?"
        return "Treba mi jos jedan podatak da bih nastavila."

    if language == "de":
        if "date" in missing and "customer_contact" in missing:
            return "Ich kann helfen. Ich brauche Datum und Name oder Telefonnummer des Kunden."
        if "date" in missing:
            return "Fuer welches Datum moechten Sie den Termin?"
        if "customer_contact" in missing:
            return "Ich brauche Name oder Telefonnummer des Kunden, um den Termin sicher zu buchen."
        if "service" in missing:
            return service_clarifying_response(business_client, language, customer_memory)
        if "appointment_target" in missing:
            return "Ich brauche Name, Telefon oder den genauen Termin, um die Buchung zu finden."
        if "new_date" in missing and "new_time" in missing:
            return "Auf welches Datum und welche Uhrzeit moechten Sie den Termin verschieben?"
        if "new_date" in missing:
            return "Auf welches Datum moechten Sie den Termin verschieben?"
        if "new_time" in missing:
            return "Zu welcher Uhrzeit soll der neue Termin sein?"
        if "intent" in missing:
            return "Bitte schreiben Sie, ob Sie buchen, absagen, verschieben oder einen Termin pruefen moechten."
        if suggestions:
            return f"Ich kann diese Termine anbieten: {suggestions}. Welcher passt?"
        return "Ich brauche noch eine Angabe, um fortzufahren."

    if "date" in missing and "customer_contact" in missing:
        return "I can help. I need the appointment date and the customer's name or phone number."
    if "date" in missing:
        return "Which date would you like for the appointment?"
    if "customer_contact" in missing:
        return "I need the customer's name or phone number before I can safely book the appointment."
    if "service" in missing:
        return service_clarifying_response(business_client, language, customer_memory)
    if "appointment_target" in missing:
        return "I need the name, phone number or exact appointment so I can find the booking."
    if "new_date" in missing and "new_time" in missing:
        return "Which date and time should I move the appointment to?"
    if "new_date" in missing:
        return "Which date should I move the appointment to?"
    if "new_time" in missing:
        return "What time should the new appointment be?"
    if "intent" in missing:
        return "Please tell me whether you want to book, cancel, reschedule or check an appointment."
    if suggestions:
        return f"I can offer these available times: {suggestions}. Which one works for you?"
    return "I need one more detail before I can continue."


def save_conversation_ai_state(conversation, intent_name, payload, tool_output, missing_fields, language, confidence):
    if not conversation:
        return {}

    metadata = conversation.metadata or {}
    previous_state = metadata.get("ai_state") or {}
    if not isinstance(previous_state, dict):
        previous_state = {}

    unknown_count = 0
    if intent_name == "unknown":
        unknown_count = int(previous_state.get("unknown_count") or 0) + 1
    elif intent_name == "support_handoff":
        unknown_count = int(previous_state.get("unknown_count") or 0)

    tool_status = (tool_output or {}).get("status", "")
    waiting_statuses = {"needs_more_details", "needs_time", "needs_target", "time_unavailable", "failed"}
    state_status = "handoff" if intent_name == "support_handoff" else "open"
    if missing_fields or tool_status in waiting_statuses:
        state_status = "waiting_for_customer"
    if tool_status in {"booked", "cancelled", "rescheduled"}:
        state_status = "completed"

    appointment_id = (tool_output or {}).get("appointment_id") or previous_state.get("last_appointment_id")
    appointment_date = (tool_output or {}).get("date") or previous_state.get("last_appointment_date")
    appointment_time = (tool_output or {}).get("time") or previous_state.get("last_appointment_time")
    pending_payload = payload if state_status == "waiting_for_customer" else {}
    state = {
        "status": state_status,
        "last_intent": intent_name,
        "last_confidence": float(confidence),
        "missing_fields": missing_fields or [],
        "pending_payload": json_safe(pending_payload),
        "last_tool_status": tool_status,
        "unknown_count": unknown_count,
    }
    if appointment_id:
        state["last_appointment_id"] = appointment_id
    if appointment_date:
        state["last_appointment_date"] = appointment_date
    if appointment_time:
        state["last_appointment_time"] = appointment_time
    metadata["ai_state"] = state
    conversation.metadata = metadata
    conversation.language = language
    conversation.last_message_at = timezone.now()
    if state_status == "handoff":
        conversation.status = "handoff"
    elif state_status == "waiting_for_customer":
        conversation.status = "waiting"
    elif conversation.status != "closed":
        conversation.status = "open"
    conversation.save(update_fields=["metadata", "language", "last_message_at", "status", "updated_at"])
    return state


def write_ai_tool_audit(business_client, tool_run, channel, intent_name, confidence, tool_output, preprocess):
    try:
        write_audit_log(
            "ai_agent.tool_run",
            business_client=business_client,
            object_type="AIToolRun",
            object_id=tool_run.id,
            channel=channel,
            metadata=json_safe(
                {
                    "intent": intent_name,
                    "confidence": float(confidence),
                    "tool_name": tool_run.tool_name,
                    "status": tool_run.status,
                    "tool_output_status": (tool_output or {}).get("status", ""),
                    "preprocess": preprocess,
                }
            ),
        )
    except Exception:
        return None
    return True


def build_workflow_trace(intent_name, tool_name, status, missing_fields, preprocess, tool_output):
    return json_safe(
        {
            "steps": {
                "preprocess": {
                    "language": preprocess.get("language"),
                    "customer_identified": preprocess.get("customer_identified"),
                    "no_show_risk": preprocess.get("no_show_risk"),
                    "date_hint_present": preprocess.get("date_hint_present"),
                    "time_hint_present": preprocess.get("time_hint_present"),
                },
                "understand": {"intent": intent_name},
                "route": {"tool_name": tool_name},
                "collect_missing_data": {"missing_fields": missing_fields or []},
                "execute_backend_tool": {
                    "status": status,
                    "tool_output_status": (tool_output or {}).get("status", ""),
                },
                "respond": {"response_language": (tool_output or {}).get("response_language")},
                "audit": {"enabled": True},
            }
        }
    )


def knowledge_entries_for_client(business_client, language):
    return list(
        BusinessKnowledgeEntry.objects.filter(
            business_client=business_client,
            is_active=True,
            language__in=[language, business_client.interface_language or business_client.language or "en", "en"],
        )
        .order_by("category", "title")
        .values("id", "category", "language", "title", "answer", "keywords")[:50]
    )


def score_knowledge_entry(text, entry):
    normalized = (text or "").lower()
    haystack = " ".join(
        str(entry.get(key) or "").lower()
        for key in ("title", "keywords", "category")
    )
    score = 0
    for token in re.findall(r"\w+", normalized):
        if len(token) < 3:
            continue
        if token in haystack:
            score += 1
    return score


def match_knowledge_entry(business_client, text, language):
    candidates = knowledge_entries_for_client(business_client, language)
    ranked = sorted(
        ((score_knowledge_entry(text, entry), entry) for entry in candidates),
        key=lambda item: item[0],
        reverse=True,
    )
    if ranked and ranked[0][0] > 0:
        return ranked[0][1]
    return None


def normalize_phone_identity(value):
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits if len(digits) >= 6 else ""


def normalize_text_identity(value):
    return str(value or "").strip().lstrip("@").casefold()


def customer_identity_entries(payload=None, customer=None):
    payload = payload or {}
    entries = {}
    phone = normalize_phone_identity(payload.get("phone") or (customer.phone if customer else ""))
    email = normalize_text_identity(payload.get("email") or (customer.email if customer else ""))
    telegram_username = normalize_text_identity(payload.get("telegram_username"))
    telegram_user_id = str(payload.get("telegram_user_id") or "").strip()
    telegram_chat_id = str(payload.get("telegram_chat_id") or "").strip()

    if phone:
        entries["phone"] = phone
    if email:
        entries["email"] = email
    if telegram_username:
        entries["telegram_username"] = telegram_username
    if telegram_user_id:
        entries["telegram_user_id"] = telegram_user_id
    if telegram_chat_id:
        entries["telegram_chat_id"] = telegram_chat_id
    return entries


def find_customer_by_payload_identity(business_client, payload=None):
    payload = payload or {}
    phone = normalize_phone_identity(payload.get("phone"))
    if phone:
        customer = Customer.objects.filter(business_client=business_client, phone__icontains=phone[-6:]).first()
        if customer:
            return customer

    email = normalize_text_identity(payload.get("email"))
    if email:
        customer = Customer.objects.filter(business_client=business_client, email__iexact=email).first()
        if customer:
            return customer

    for key, value in customer_identity_entries(payload).items():
        memory = (
            CustomerMemory.objects.select_related("customer")
            .filter(business_client=business_client, **{f"identifiers__{key}": value})
            .first()
        )
        if memory:
            return memory.customer
    return None


def appointment_from_tool_output(business_client, tool_output):
    appointment_id = (tool_output or {}).get("appointment_id")
    if not appointment_id:
        return None
    return (
        business_client.appointments.select_related("customer", "service", "staff_member")
        .filter(id=appointment_id)
        .first()
    )


def increment_memory_preference(preferences, group, key):
    preferences = dict(preferences or {})
    if not key:
        return preferences
    group_values = dict(preferences.get(group) or {})
    group_values[key] = int(group_values.get(key) or 0) + 1
    preferences[group] = group_values
    return preferences


def top_memory_preference(preferences, group):
    values = (preferences or {}).get(group) or {}
    if not isinstance(values, dict) or not values:
        return "", 0
    key, count = sorted(values.items(), key=lambda item: item[1], reverse=True)[0]
    return key, int(count or 0)


def calculate_no_show_risk(total_count, cancellation_count):
    if total_count >= 3 and cancellation_count / max(total_count, 1) >= 0.5:
        return CustomerMemory.RISK_HIGH
    if cancellation_count:
        return CustomerMemory.RISK_MEDIUM
    return CustomerMemory.RISK_LOW


def build_customer_memory_summary(customer, appointment, memory, channel):
    parts = [f"{customer.full_name} has {memory.appointment_count} active appointment records with this business."]
    if appointment.service_id:
        parts.append(f"Last service: {appointment.service.name}.")
    if appointment.staff_member_id:
        parts.append(f"Last staff member: {appointment.staff_member.full_name}.")
    if channel:
        parts.append(f"Recent channel: {channel}.")
    if memory.no_show_risk != CustomerMemory.RISK_LOW:
        parts.append(f"Reliability note: {memory.no_show_risk} cancellation risk.")
    return " ".join(parts)


def build_customer_routine_notes(memory):
    service, service_count = top_memory_preference(memory.preferences, "services")
    staff_member, staff_count = top_memory_preference(memory.preferences, "staff_members")
    notes = []
    if service and service_count >= 2:
        notes.append(f"Often books {service}.")
    if staff_member and staff_count >= 2:
        notes.append(f"Often chooses {staff_member}.")
    return " ".join(notes)


def customer_memory_context(customer):
    if not customer:
        return {}
    memory = CustomerMemory.objects.filter(customer=customer).select_related("last_service", "preferred_staff_member").first()
    if not memory:
        return {}
    return {
        "customer_id": customer.id,
        "customer_name": customer.full_name,
        "summary": memory.summary,
        "routine_notes": memory.routine_notes,
        "preferences": memory.preferences,
        "identifiers": memory.identifiers,
        "appointment_count": memory.appointment_count,
        "cancellation_count": memory.cancellation_count,
        "reschedule_count": memory.reschedule_count,
        "no_show_risk": memory.no_show_risk,
        "last_service": memory.last_service.name if memory.last_service_id else "",
        "preferred_staff_member": memory.preferred_staff_member.full_name if memory.preferred_staff_member_id else "",
        "favorite_service": top_memory_preference(memory.preferences, "services")[0],
        "favorite_time": top_memory_preference(memory.preferences, "times")[0],
        "last_seen_at": memory.last_seen_at.isoformat() if memory.last_seen_at else "",
    }


def update_customer_memory_from_tool_output(business_client, conversation, intent_name, tool_output, channel, payload=None):
    appointment = appointment_from_tool_output(business_client, tool_output)
    if not appointment or not appointment.customer_id:
        return {}

    customer = appointment.customer
    if conversation and conversation.customer_id != customer.id:
        conversation.customer = customer
        conversation.save(update_fields=["customer", "updated_at"])

    memory, _ = CustomerMemory.objects.get_or_create(
        business_client=business_client,
        customer=customer,
    )
    preferences = memory.preferences if isinstance(memory.preferences, dict) else {}
    preferences = increment_memory_preference(preferences, "channels", channel)
    preferences = increment_memory_preference(preferences, "times", appointment.start_time.strftime("%H:%M"))
    if appointment.service_id:
        preferences = increment_memory_preference(preferences, "services", appointment.service.name)
    if appointment.staff_member_id:
        preferences = increment_memory_preference(preferences, "staff_members", appointment.staff_member.full_name)
    identifiers = memory.identifiers if isinstance(memory.identifiers, dict) else {}
    identifiers.update(customer_identity_entries(payload, customer=customer))

    appointment_count = business_client.appointments.filter(
        customer=customer,
        status__in=[Appointment.STATUS_CONFIRMED, Appointment.STATUS_MOVED, Appointment.STATUS_PENDING],
    ).count()
    cancellation_count = business_client.appointments.filter(customer=customer, status=Appointment.STATUS_CANCELLED).count()
    reschedule_count = business_client.appointments.filter(customer=customer, status=Appointment.STATUS_MOVED).count()
    total_count = appointment_count + cancellation_count

    memory.preferences = preferences
    memory.identifiers = identifiers
    memory.last_service = appointment.service
    memory.preferred_staff_member = appointment.staff_member
    memory.appointment_count = appointment_count
    memory.cancellation_count = cancellation_count
    memory.reschedule_count = reschedule_count
    memory.no_show_risk = calculate_no_show_risk(total_count, cancellation_count)
    memory.last_seen_at = timezone.now()
    memory.last_appointment_at = appointment.updated_at
    memory.summary = build_customer_memory_summary(customer, appointment, memory, channel)
    memory.routine_notes = build_customer_routine_notes(memory)
    memory.save(
        update_fields=[
            "preferences",
            "identifiers",
            "last_service",
            "preferred_staff_member",
            "appointment_count",
            "cancellation_count",
            "reschedule_count",
            "no_show_risk",
            "last_seen_at",
            "last_appointment_at",
            "summary",
            "routine_notes",
            "updated_at",
        ]
    )
    return customer_memory_context(customer)


def queue_ai_follow_up_jobs(business_client, intent_name, tool_output, language):
    event_by_status = {
        "booked": "appointment_created",
        "rescheduled": "appointment_changed",
        "cancelled": "appointment_cancelled",
        "handoff": "support_needed",
    }
    tool_status = (tool_output or {}).get("status", "")
    event = event_by_status.get(tool_status)
    if intent_name == "support_handoff":
        event = "support_needed"
    if not event:
        return []

    appointment = None
    appointment_id = (tool_output or {}).get("appointment_id")
    if appointment_id:
        appointment = business_client.appointments.filter(id=appointment_id).select_related("customer").first()

    customer = appointment.customer if appointment and appointment.customer_id else None
    return queue_notification_jobs_for_event(
        business_client,
        event,
        appointment=appointment,
        customer=customer,
        language=language,
        payload={
            "intent": intent_name,
            "tool_status": tool_status,
            "appointment_id": appointment_id,
            "customer": (tool_output or {}).get("customer", ""),
            "date": (tool_output or {}).get("date", ""),
            "time": (tool_output or {}).get("time", ""),
        },
    )


def support_priority_from_text(text):
    lowered = (text or "").lower()
    urgent_words = ("hitno", "urgent", "emergency", "zalba", "complaint", "angry", "problem")
    return SupportTicket.PRIORITY_URGENT if any(word in lowered for word in urgent_words) else SupportTicket.PRIORITY_NORMAL


def create_support_ticket_for_handoff(
    business_client,
    conversation,
    text,
    channel,
    language,
    preprocess,
    planner_raw_response,
    payload=None,
):
    existing = None
    if conversation:
        existing = (
            SupportTicket.objects.filter(
                business_client=business_client,
                metadata__conversation_id=conversation.id,
                status__in=(SupportTicket.STATUS_OPEN, SupportTicket.STATUS_IN_PROGRESS),
            )
            .order_by("-created_at")
            .first()
        )
    if existing:
        return existing

    payload = payload or {}
    requester = conversation.customer if conversation and conversation.customer else None
    requester_name = requester.full_name if requester else (payload.get("customer_name") or payload.get("name") or "")
    requester_phone = requester.phone if requester else (payload.get("phone") or payload.get("customer_phone") or "")
    requester_email = requester.email if requester else (payload.get("email") or payload.get("customer_email") or "")

    subject = f"Kaleya support handoff - {channel or 'web'}"
    message = (
        "Kaleya nije mogla samostalno da zavrsi zahtev.\n\n"
        f"Kanal: {channel or 'web'}\n"
        f"Jezik: {language or 'en'}\n"
        f"Klijent: {requester_name or 'Nepoznato'}\n"
        f"Telefon: {requester_phone or 'Nepoznato'}\n"
        f"Email: {requester_email or 'Nepoznato'}\n"
        f"Poruka korisnika: {text or ''}"
    )
    return SupportTicket.objects.create(
        business_client=business_client,
        subject=subject[:180],
        message=message,
        priority=support_priority_from_text(text),
        status=SupportTicket.STATUS_OPEN,
        metadata={
            "source": "ai_agent",
            "conversation_id": conversation.id if conversation else None,
            "channel": channel,
            "language": language,
            "requester_name": requester_name,
            "requester_phone": requester_phone,
            "requester_email": requester_email,
            "input_text": text,
            "payload": json_safe(payload),
            "preprocess": json_safe(preprocess),
            "planner": json_safe(planner_raw_response),
        },
    )


def actor_scope_for_ai(actor):
    if user_role(actor) != "employee":
        return {"role": user_role(actor) or "", "staff_member": None}
    return {"role": "employee", "staff_member": getattr(actor, "staff_member_profile", None)}


def apply_actor_scope_to_payload(business_client, actor, intent_name, payload):
    scope = actor_scope_for_ai(actor)
    staff_member = scope["staff_member"]
    if scope["role"] != "employee":
        return payload, ""
    if not staff_member or staff_member.business_client_id != business_client.id:
        return payload, "employee_staff_missing"

    payload = {**(payload or {})}
    if intent_name in {"book_appointment", "check_availability", "reschedule_appointment", "cancel_appointment"}:
        payload["staff_member_id"] = staff_member.id
    if intent_name == "cancel_appointment" and payload.get("appointment_id"):
        allowed = business_client.appointments.filter(
            id=payload["appointment_id"],
            staff_member_id=staff_member.id,
        ).exists()
        if not allowed:
            return payload, "employee_forbidden_appointment"
    return payload, ""


def recent_conversation_messages(conversation, limit=6):
    if not conversation:
        return []
    messages = list(conversation.messages.order_by("-created_at")[:limit])
    messages.reverse()
    return [
        {
            "direction": message.direction,
            "sender": message.sender_label,
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }
        for message in messages
    ]


def build_planner_context(business_client, conversation=None, conversation_state=None, customer=None):
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
    language = business_client.interface_language or business_client.language or "en"
    context = {
        "today": client_local_today(business_client).isoformat(),
        "business": {
            "id": business_client.id,
            "name": business_client.public_name or business_client.name,
            "language": language,
            "timezone": business_client.timezone,
            "work_start": business_client.work_start.strftime("%H:%M"),
            "work_end": business_client.work_end.strftime("%H:%M"),
            "slot_interval_minutes": business_client.slot_interval_minutes,
        },
        "services": services,
        "staff_members": staff_members,
        "knowledge_entries": knowledge_entries_for_client(business_client, language)[:20],
    }
    if conversation_state:
        context["conversation_state"] = json_safe(conversation_state)
    memory_customer = customer or (conversation.customer if conversation and conversation.customer_id else None)
    if memory_customer:
        context["customer_memory"] = customer_memory_context(memory_customer)
    if conversation:
        context["recent_messages"] = recent_conversation_messages(conversation)
    return context


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


def should_resume_previous_intent(intent_name, previous_state):
    if intent_name != "unknown":
        return False
    if not previous_state or previous_state.get("status") != "waiting_for_customer":
        return False
    return previous_state.get("last_intent") in RESUMABLE_INTENTS


def resume_previous_intent(previous_state):
    return previous_state.get("last_intent"), safe_float(previous_state.get("last_confidence"), 0.72)


def should_treat_as_reschedule_followup(intent_name, previous_state, text, payload):
    if not previous_state or previous_state.get("status") != "completed":
        return False
    if previous_state.get("last_intent") not in {"book_appointment", "reschedule_appointment"}:
        return False
    if not previous_state.get("last_appointment_id"):
        return False
    if intent_name not in AMBIGUOUS_COMPLETED_FOLLOWUP_INTENTS:
        return False
    if intent_name == "book_appointment" and contains_normalized_hint(text, BOOKING_ACTION_HINTS):
        return False
    return bool(payload.get("date") or payload.get("time") or text_has_date_hint(text) or parse_requested_time(text))


def attach_last_appointment_to_payload(payload, previous_state):
    if not previous_state or not previous_state.get("last_appointment_id"):
        return payload
    payload = {**(payload or {})}
    payload.setdefault("appointment_id", previous_state["last_appointment_id"])
    return payload


def build_text_response(business_client, intent, tool_output):
    language = tool_output.get("response_language") or business_client.interface_language or business_client.language or "en"

    if tool_output.get("status") == "needs_more_details":
        return build_clarifying_response(business_client, intent, tool_output.get("missing_fields", []), tool_output)

    if intent == "check_availability":
        count = tool_output.get("free_count", 0)
        suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
        return localized_availability_response(language, count, suggestions)

    if intent == "book_appointment":
        status = tool_output.get("status")
        suggestions = memory_prioritized_suggestions(tool_output)
        if status == "booked":
            return localized_status_response(
                BOOKING_RESPONSE_TEMPLATES,
                "booked",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
                suggestions=suggestions,
            )
        if status == "needs_time":
            return localized_status_response(
                BOOKING_RESPONSE_TEMPLATES,
                "needs_time",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
                suggestions=suggestions,
            )
        if status == "time_unavailable":
            return localized_status_response(
                BOOKING_RESPONSE_TEMPLATES,
                "time_unavailable",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
                suggestions=suggestions,
            )

    if intent == "cancel_appointment":
        if tool_output.get("status") == "cancelled":
            return localized_status_response(CANCEL_RESPONSE_TEMPLATES, "cancelled", language)
        return localized_status_response(CANCEL_RESPONSE_TEMPLATES, "target_missing", language)

    if intent == "reschedule_appointment":
        suggestions = memory_prioritized_suggestions(tool_output)
        if tool_output.get("status") == "rescheduled":
            return localized_status_response(
                RESCHEDULE_RESPONSE_TEMPLATES,
                "rescheduled",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
            )
        if tool_output.get("status") == "needs_time":
            return localized_status_response(
                RESCHEDULE_RESPONSE_TEMPLATES,
                "needs_time",
                language,
                date=tool_output.get("date"),
                suggestions=suggestions,
            )
        return localized_status_response(RESCHEDULE_RESPONSE_TEMPLATES, "missing_new_time", language)

    if intent == "support_handoff":
        if language == "sr":
            return "Razumem. Prebacujem zahtev support timu."
        if language == "de":
            return "Ich verstehe. Ich uebergebe die Anfrage an das Support-Team."
        return "I understand. I am handing this over to support."

    if intent == "business_info":
        matched_knowledge = tool_output.get("matched_knowledge") or {}
        if matched_knowledge.get("answer"):
            return matched_knowledge["answer"]
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

    if intent == "unknown":
        if language == "sr":
            return "Nisam sigurna da sam dobro razumela. Mozete li napisati da li zelite zakazivanje, otkazivanje, pomeranje ili proveru termina?"
        if language == "de":
            return "Ich bin nicht sicher, ob ich richtig verstanden habe. Geht es um Buchen, Absagen, Verschieben oder Pruefen eines Termins?"
        return "I am not fully sure I understood. Do you want to book, cancel, reschedule or check an appointment?"

    if language == "sr":
        return "Razumem zahtev. Sledeci korak je provera kalendara i potvrda termina."
    return "I understand the request. The next step is checking the calendar and confirming the appointment."


def build_system_prompt(business_client):
    language = business_client.interface_language or business_client.language or "en"
    prompt = (
        "Ti si Kaleya, profesionalna AI sekretarica za zakazivanje termina. "
        "Odgovaraj kratko, jasno i ljubazno. "
        "Ne izmisljaj termine. Tool output je jedini izvor istine za kalendar. "
        "Ako tool output sadrzi free_count, date ili suggested_slots, ne smes reci da ne vidis kalendar ili da nemas datum. "
        "Ako safe_deterministic_response postoji u kontekstu, koristi ga kao proverenu osnovu i samo ga prirodnije formuliši. "
        "Ne koristi emoji. "
        "Ako korisnik trazi nesto sto ne mozes da potvrdis kroz tool output, reci da ces proveriti ili prebaciti supportu. "
        f"Jezik odgovora mora biti: {language}."
    )
    try:
        master_prompt = (business_client.api_settings.master_prompt or "").strip()
    except ClientApiSettings.DoesNotExist:
        master_prompt = ""
    if master_prompt:
        prompt = f"{prompt}\n\nDodatna pravila za ovog klijenta:\n{master_prompt}"
    return prompt


def handle_inbound_text(
    business_client,
    text,
    conversation=None,
    customer=None,
    channel="web",
    payload=None,
    use_ai=True,
    include_voice=False,
    external_thread_id="",
    record_messages=True,
    actor=None,
):
    payload = payload or {}
    if not customer:
        customer = find_customer_by_payload_identity(business_client, payload)
    planner_raw_response = {"engine": "keyword-fallback"}
    planner_payload = {}
    intent_name, confidence = detect_intent(text)
    initial_language = detect_message_language(text, business_client.interface_language or business_client.language or "en")
    conversation = ensure_workflow_conversation(
        business_client,
        conversation=conversation,
        customer=customer,
        channel=channel,
        external_thread_id=external_thread_id,
        language=initial_language,
    )
    if not customer and conversation and conversation.customer:
        customer = conversation.customer
    payload = merge_conversation_payload(conversation, payload)
    if not customer:
        customer = find_customer_by_payload_identity(business_client, payload)
        if customer and conversation and conversation.customer_id != customer.id:
            conversation.customer = customer
            conversation.save(update_fields=["customer", "updated_at"])
    previous_state = get_conversation_ai_state(conversation)
    inbound_message = None
    if record_messages:
        inbound_message = write_workflow_message(
            conversation,
            "inbound",
            text,
            sender_label="Customer",
            raw_payload={"channel": channel, "payload": json_safe(payload), "external_thread_id": external_thread_id},
        )

    if use_ai:
        try:
            planner = generate_anthropic_plan(
                business_client,
                text,
                context=build_planner_context(
                    business_client,
                    conversation=conversation,
                    conversation_state=previous_state,
                    customer=customer,
                ),
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
    if should_resume_previous_intent(intent_name, previous_state):
        intent_name, confidence = resume_previous_intent(previous_state)
        planner_raw_response["resumed_from_previous_state"] = True
    if intent_name == "reschedule_appointment":
        payload = attach_last_appointment_to_payload(payload, previous_state)
    elif should_treat_as_reschedule_followup(intent_name, previous_state, text, payload):
        intent_name = "reschedule_appointment"
        confidence = max(confidence, 0.74)
        payload = attach_last_appointment_to_payload(payload, previous_state)
        planner_raw_response["resumed_from_completed_appointment"] = True
    payload = infer_payload_from_text(business_client, text, payload)
    preprocess = build_preprocess_context(
        business_client,
        text,
        customer=customer,
        payload=payload,
        channel=channel,
        language_fallback=conversation.language if conversation else "",
    )
    language = preprocess["language"]
    current_customer_memory = customer_memory_context(customer)
    matched_knowledge = match_knowledge_entry(business_client, text, language)
    if intent_name == "unknown" and matched_knowledge:
        intent_name = "business_info"
        confidence = max(confidence, 0.78)
        planner_raw_response["knowledge_match"] = matched_knowledge

    payload, scope_error = apply_actor_scope_to_payload(business_client, actor, intent_name, payload)
    if scope_error:
        intent_name = "support_handoff"
        confidence = max(confidence, 0.7)
        planner_raw_response["scope_error"] = scope_error

    unknown_count = int(previous_state.get("unknown_count") or 0)
    if confidence < LOW_CONFIDENCE_THRESHOLD and intent_name == "unknown" and unknown_count + 1 >= MAX_UNKNOWN_BEFORE_HANDOFF:
        intent_name = "support_handoff"
        confidence = max(confidence, LOW_CONFIDENCE_THRESHOLD)
        planner_raw_response["handoff_reason"] = "low_confidence_repeated"

    missing_fields = []
    missing_fields = workflow_missing_fields(business_client, intent_name, text, payload, customer=customer)
    if intent_name == "unknown":
        missing_fields = ["intent"]

    intent = AIIntent.objects.create(
        business_client=business_client,
        conversation=conversation,
        customer=customer,
        intent=intent_name,
        confidence=confidence,
        input_text=text or "",
        language=language,
        raw_response=json_safe({**planner_raw_response, "preprocess": preprocess}),
    )

    tool_output = {}
    tool_name = "none"
    status = "skipped"

    if missing_fields:
        tool_name = "clarify_missing_data"
        tool_output = {
            "status": "needs_more_details",
            "missing_fields": missing_fields,
            "pending_payload": json_safe(payload),
            "customer_memory": current_customer_memory,
        }
        status = "planned"
    elif intent_name == "check_availability":
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
        tool_output = {"status": "handoff", "handoff": True, "channel": channel}
        status = "success"
    elif intent_name == "business_info":
        tool_name = "business_info"
        tool_output = {
            "business_name": business_client.public_name or business_client.name,
            "work_start": business_client.work_start.strftime("%H:%M"),
            "work_end": business_client.work_end.strftime("%H:%M"),
            "slot_interval_minutes": business_client.slot_interval_minutes,
            "matched_knowledge": matched_knowledge or {},
        }
        status = "success"
    elif intent_name == "unknown":
        tool_name = "clarify_intent"
        tool_output = {"status": "needs_more_details", "missing_fields": ["intent"]}
        status = "planned"

    tool_output.setdefault("response_language", language)
    if current_customer_memory:
        tool_output.setdefault("customer_memory", current_customer_memory)

    tool_run = AIToolRun.objects.create(
        business_client=business_client,
        intent=intent,
        tool_name=tool_name,
        status=status,
        input_payload=json_safe({"text": text, "channel": channel, "payload": payload}),
        output_payload=json_safe(tool_output),
    )
    if intent_name == "support_handoff":
        support_ticket = create_support_ticket_for_handoff(
            business_client,
            conversation,
            text,
            channel,
            language,
            preprocess,
            planner_raw_response,
            payload,
        )
        tool_output["support_ticket_id"] = support_ticket.id
        tool_run.output_payload = json_safe(tool_output)
        tool_run.save(update_fields=["output_payload"])
    customer_memory = update_customer_memory_from_tool_output(
        business_client,
        conversation,
        intent_name,
        tool_output,
        channel,
        payload,
    ) or current_customer_memory
    conversation_state = save_conversation_ai_state(
        conversation,
        intent_name,
        payload,
        tool_output,
        missing_fields,
        language,
        confidence,
    )
    write_ai_tool_audit(business_client, tool_run, channel, intent_name, confidence, tool_output, preprocess)
    follow_up_jobs = queue_ai_follow_up_jobs(business_client, intent_name, tool_output, language)
    workflow_trace = build_workflow_trace(intent_name, tool_name, status, missing_fields, preprocess, tool_output)

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
                    "decision": {
                        "tool_name": tool_name,
                        "status": status,
                        "missing_fields": missing_fields,
                        "conversation_state": conversation_state,
                        "customer_memory": customer_memory,
                        "follow_up_job_count": len(follow_up_jobs),
                    },
                    "preprocess": preprocess,
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

    outbound_message = None
    if record_messages:
        outbound_message = write_workflow_message(
            conversation,
            "outbound",
            response_text,
            sender_label="Kaleya",
            raw_payload={
                "intent_id": intent.id,
                "tool_run_id": tool_run.id,
                "tool_output": json_safe(tool_output),
                "workflow_trace": workflow_trace,
            },
        )

    return {
        "intent": intent.intent,
        "confidence": float(intent.confidence),
        "response_text": response_text,
        "ai_provider": ai_provider_used,
        "voice": voice,
        "tool_output": tool_output,
        "decision": {
            "tool_name": tool_name,
            "status": status,
            "missing_fields": missing_fields,
        },
        "preprocess": preprocess,
        "conversation_state": conversation_state,
        "customer_memory": customer_memory,
        "workflow_trace": workflow_trace,
        "conversation_id": conversation.id if conversation else None,
        "follow_up_jobs": [job.id for job in follow_up_jobs],
        "messages": {
            "inbound_id": inbound_message.id if inbound_message else None,
            "outbound_id": outbound_message.id if outbound_message else None,
        },
    }
