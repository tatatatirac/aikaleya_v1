import json
import re
import unicodedata
from datetime import date, timedelta

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
    parse_bare_day_of_month_date,
    parse_requested_date,
    parse_requested_time,
    parse_time_period_preference,
    reschedule_appointment_tool,
    text_has_parseable_date,
)
from accounts.permissions import user_role
from appointments.services import client_timezone
from audit_log.services import write_audit_log
from appointments.models import Appointment, Customer
from clients.models import BusinessKnowledgeEntry, ClientApiSettings
from communications.models import Conversation, Message
from notifications.services import queue_notification_jobs_for_event
from staff_services.models import Service, StaffMember, WorkingHours
from support.models import SupportTicket


SERBIAN_CYRILLIC_TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "ђ": "dj",
        "е": "e",
        "ж": "z",
        "з": "z",
        "и": "i",
        "ј": "j",
        "к": "k",
        "л": "l",
        "љ": "lj",
        "м": "m",
        "н": "n",
        "њ": "nj",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "ћ": "c",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "c",
        "ч": "c",
        "џ": "dz",
        "ш": "s",
        "А": "a",
        "Б": "b",
        "В": "v",
        "Г": "g",
        "Д": "d",
        "Ђ": "dj",
        "Е": "e",
        "Ж": "z",
        "З": "z",
        "И": "i",
        "Ј": "j",
        "К": "k",
        "Л": "l",
        "Љ": "lj",
        "М": "m",
        "Н": "n",
        "Њ": "nj",
        "О": "o",
        "П": "p",
        "Р": "r",
        "С": "s",
        "Т": "t",
        "Ћ": "c",
        "У": "u",
        "Ф": "f",
        "Х": "h",
        "Ц": "c",
        "Ч": "c",
        "Џ": "dz",
        "Ш": "s",
    }
)


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
    "ima li popodne",
    "ima li posle podne",
    "ima li prepodne",
    "ima li pre podne",
    "ima li sta",
    "ima li nesto",
    "ima li termina",
    "ima termina",
    "ima li termin",
    "ima nesto",
    "ima neki",
    "sta ima",
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
    "zalazem",
    "zalažem",
    "zakaži",
    "zakazivanje",
    "rezervisi",
    "rezerviši",
    "book",
    "reserve",
    "schedule",
    "zakazem",
    "zakazati",
    "rezervisati",
)
NATURAL_BOOKING_REQUEST_HINTS = (
    "treba mi",
    "potreban mi",
    "potrebno mi",
    "zelim",
    "želim",
    "hocu",
    "hoću",
    "hteo bih",
    "htela bih",
    "moze li",
    "jel moze",
    "je l moze",
    "je li moze",
    "može li",
    "da ako moze",
    "da ako može",
    "i need",
    "i want",
    "can i",
    "could i",
)
AVAILABILITY_REFINEMENT_HINTS = (
    "ali",
    "oko",
    "around",
    "about",
    "near",
    "blizu",
)
BOOKING_CONFIRMATION_HINTS = (
    "moze",
    "moze li",
    "odgovara",
    "zakazi",
    "rezervisi",
    "rezervisati",
    "book",
    "reserve",
    "yes",
)
SHORT_CONFIRMATION_HINTS = (
    "moze",
    "moze moze",
    "da",
    "da moze",
    "hocu",
    "hoću",
    "zelim",
    "želim",
    "da zelim",
    "da želim",
    "da kao i uvek",
    "da kao i uvijek",
    "kao i uvek",
    "kao i uvijek",
    "da rekao sam vec",
    "da rekao sam već",
    "ok",
    "okej",
    "u redu",
    "vazi",
    "moze to",
    "odgovara",
    "yes",
    "sure",
    "ok yes",
)
GREETING_HINTS = (
    "start",
    "hi",
    "ej",
    "alo",
    "aloo",
    "alooo",
    "hello",
    "helo",
    "ahoj",
    "hey",
    "pozdrav",
    "cao",
    "zdravo",
    "bardan",
    "dobar dan",
    "dobardan",
    "dobro jutro",
    "dobrojutro",
    "dobro vece",
    "dobrovece",
    "good morning",
    "goodmorning",
    "good afternoon",
    "goodafternoon",
    "good evening",
    "goodevening",
    "hola",
    "bonjour",
    "ciao",
    "hallo",
    "privet",
)
GRATITUDE_HINTS = (
    "fala",
    "fala vi",
    "fala vam",
    "hvala",
    "hvala vam",
    "hvala vama",
    "hvala puno",
    "zahvaljujem",
    "thanks",
    "thank you",
    "thankyou",
    "tnx",
    "danke",
    "gracias",
    "merci",
    "grazie",
    "obrigado",
    "obrigada",
)
CLOSING_HINTS = (
    "dovidenja",
    "dovidjenja",
    "doviđenja",
    "doviđenja",
    "vidimo se",
    "vidimo se cao",
    "cao vidimo se",
    "prijatno",
    "cao cao",
    "bye",
    "goodbye",
    "see you",
)
COMPLETED_FLOW_CLOSING_HINTS = (
    "cao",
    "ćao",
    "ok",
    "okej",
    "u redu",
    "uredu",
    "vazi",
    "važi",
    "dogovoreno",
    "super",
    "odlicno",
    "odlično",
)
CUSTOMER_INFO_HINTS = (
    "imate li moj telefon",
    "imas li moj telefon",
    "moj telefon",
    "moj broj",
    "koji je moj telefon",
    "koji je moj broj",
    "moje ime",
    "kako se zovem",
    "moji podaci",
    "my phone",
    "my number",
    "my name",
)
ABUSIVE_HINTS = (
    "jebi",
    "odjebi",
    "jebem",
    "jebote",
    "mars",
    "marš",
    "idiot",
    "budalo",
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
    ("de", ("termin", "buchen", "absagen", "frei", "morgen", "heute", "verschieb", "verschieben")),
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
    normalized = str(value or "").translate(SERBIAN_CYRILLIC_TRANSLITERATION)
    normalized = normalized.replace("đ", "dj").replace("Đ", "dj")
    normalized = unicodedata.normalize("NFKD", normalized).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.replace("đ", "dj")
    return re.sub(r"\s+", " ", normalized).strip()


def contains_normalized_hint(text, hints):
    normalized = normalize_intent_text(text)
    return any(normalize_intent_text(hint) in normalized for hint in hints)


def normalized_compact_words(text):
    return re.sub(r"[\s,!.?;:]+", " ", normalize_intent_text(text)).strip()


def normalized_alnum(text):
    return re.sub(r"[^a-z0-9]+", "", normalize_intent_text(text))


def edit_distance_at_most_one(left, right):
    if left == right:
        return True
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(1 for left_char, right_char in zip(left, right) if left_char != right_char) <= 1
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    index_short = 0
    skipped = 0
    for char in longer:
        if index_short < len(shorter) and shorter[index_short] == char:
            index_short += 1
            continue
        skipped += 1
        if skipped > 1:
            return False
    return True


def is_greeting_text(text):
    compact = normalized_compact_words(text)
    if not compact:
        return False
    greeting_phrases = tuple(normalize_intent_text(hint) for hint in GREETING_HINTS)
    if compact in greeting_phrases:
        return True
    compact_alnum = normalized_alnum(compact)
    greeting_compact_phrases = tuple(normalized_alnum(phrase) for phrase in greeting_phrases)
    if compact_alnum in greeting_compact_phrases:
        return True
    if 2 <= len(compact_alnum) <= 18 and any(edit_distance_at_most_one(compact_alnum, phrase) for phrase in greeting_compact_phrases):
        return True
    tokens = compact.split()
    if len(tokens) > 4:
        return False
    first_token_greetings = {
        "hi",
        "hello",
        "helo",
        "hey",
        "pozdrav",
        "cao",
        "zdravo",
        "bardan",
        "hola",
        "bonjour",
        "ciao",
        "hallo",
        "privet",
    }
    if tokens and tokens[0] in first_token_greetings:
        return True
    return compact.startswith((
        "dobar dan",
        "dobardan",
        "dobro jutro",
        "dobrojutro",
        "dobro vece",
        "dobrovece",
        "good morning",
        "goodmorning",
        "good afternoon",
        "goodafternoon",
        "good evening",
        "goodevening",
    ))


def is_gratitude_text(text):
    compact = normalized_compact_words(text)
    if not compact:
        return False
    compact_alnum = normalized_alnum(text)
    gratitude_phrases = tuple(normalize_intent_text(hint) for hint in GRATITUDE_HINTS)
    gratitude_compact = tuple(normalized_alnum(hint) for hint in GRATITUDE_HINTS)
    if compact in gratitude_phrases or compact_alnum in gratitude_compact:
        return True
    if "hvala" in compact_alnum or compact_alnum.endswith("fala") or compact_alnum.startswith("fala"):
        return True
    tokens = compact.split()
    return any(token in gratitude_phrases for token in tokens)


def is_conversation_closing_text(text, previous_state=None):
    compact = normalized_compact_words(text)
    compact_alnum = normalized_alnum(text)
    closing_phrases = tuple(normalize_intent_text(hint) for hint in CLOSING_HINTS)
    closing_compact = tuple(normalized_alnum(hint) for hint in CLOSING_HINTS)
    if is_gratitude_text(text) or compact in closing_phrases or compact_alnum in closing_compact:
        return True
    if any(phrase and len(phrase) >= 5 and phrase in compact for phrase in closing_phrases):
        return True
    if any(phrase and len(phrase) >= 5 and phrase in compact_alnum for phrase in closing_compact):
        return True
    previous_state = previous_state or {}
    if previous_state.get("last_tool_status") not in {"booked", "cancelled", "rescheduled"}:
        return False
    completed_phrases = tuple(normalize_intent_text(hint) for hint in COMPLETED_FLOW_CLOSING_HINTS)
    completed_compact = tuple(normalized_alnum(hint) for hint in COMPLETED_FLOW_CLOSING_HINTS)
    return compact in completed_phrases or compact_alnum in completed_compact


def is_see_you_text(text):
    compact_alnum = normalized_alnum(text)
    return "vidimose" in compact_alnum or "seeyou" in compact_alnum


def is_abusive_text(text):
    normalized = normalize_intent_text(text)
    return any(normalize_intent_text(hint) in normalized for hint in ABUSIVE_HINTS)


def is_short_confirmation_text(text):
    compact = normalized_compact_words(text)
    compact_alnum = normalized_alnum(text)
    confirmation_phrases = tuple(normalize_intent_text(hint) for hint in SHORT_CONFIRMATION_HINTS)
    confirmation_compact = tuple(normalized_alnum(hint) for hint in SHORT_CONFIRMATION_HINTS)
    return compact in confirmation_phrases or compact_alnum in confirmation_compact


def is_customer_info_question(text, previous_state=None):
    normalized = normalize_intent_text(text)
    compact = re.sub(r"[\s,!.?;:]+", " ", normalized).strip()
    if not compact:
        return False
    if any(normalize_intent_text(hint) in compact for hint in CUSTOMER_INFO_HINTS):
        return True
    if compact in {"ime", "telefon", "broj", "podaci"}:
        previous_state = previous_state or {}
        return previous_state.get("last_intent") == "business_info"
    return False


def customer_profile_payload(customer=None, payload=None):
    payload = payload or {}
    name = ""
    phone = ""
    email = ""
    if customer:
        name = customer.full_name
        phone = customer.phone
        email = customer.email
    return {
        "name": name or payload.get("customer_name") or "",
        "phone": phone or payload.get("phone") or "",
        "email": email or payload.get("email") or "",
    }


def localized_customer_profile_response(language, profile):
    name = (profile or {}).get("name") or ""
    phone = (profile or {}).get("phone") or ""
    email = (profile or {}).get("email") or ""
    if language == "sr":
        parts = []
        if name:
            parts.append(f"ime vodim kao {name}")
        if phone:
            parts.append(f"telefon kao {phone}")
        if email:
            parts.append(f"email kao {email}")
        if parts:
            return "Da, u sistemu " + ", ".join(parts) + "."
        return "Trenutno nemam sacuvane vase kontakt podatke u ovom razgovoru."
    if name or phone or email:
        parts = []
        if name:
            parts.append(f"name as {name}")
        if phone:
            parts.append(f"phone as {phone}")
        if email:
            parts.append(f"email as {email}")
        return "Yes, I have your " + ", ".join(parts) + "."
    return "I do not have your contact details saved in this conversation yet."


def localized_availability_response(language, count, suggestions):
    templates = AVAILABILITY_RESPONSE_TEMPLATES.get(language) or AVAILABILITY_RESPONSE_TEMPLATES["en"]
    template = templates[0] if suggestions else templates[1]
    return template.format(count=count, suggestions=suggestions)


def localized_time_availability_response(language, requested_time, suggestions, exact_available):
    if language == "sr":
        if exact_available:
            return f"Da, oko {requested_time} ima slobodno. Mogu da ponudim: {suggestions}."
        if suggestions:
            return f"Oko {requested_time} nije slobodno, najblize mogu da ponudim: {suggestions}."
        return f"Oko {requested_time} nema slobodnih termina."
    if language == "de":
        if exact_available:
            return f"Ja, um {requested_time} ist ein Termin frei. Ich kann anbieten: {suggestions}."
        if suggestions:
            return f"Um {requested_time} ist nichts frei. Nahe Optionen: {suggestions}."
        return f"Um {requested_time} gibt es keine freien Termine."
    if exact_available:
        return f"Yes, around {requested_time} is available. I can offer: {suggestions}."
    if suggestions:
        return f"Around {requested_time} is not available. The nearest options are: {suggestions}."
    return f"There are no available slots around {requested_time}."


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
        matched_hints = set()
        for hint in hints:
            normalized_hint = normalize_intent_text(hint)
            if normalized_hint and normalized_hint in normalized:
                matched_hints.add(normalized_hint)
        score = len(matched_hints)
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


def service_options_text(business_client, limit=6, language=None):
    language = language or business_client.interface_language or business_client.language
    services = Service.objects.filter(business_client=business_client, is_active=True).order_by("category", "name")[:limit]
    return ", ".join(localized_service_name(service.name, language) for service in services)


SERBIAN_SERVICE_DISPLAY_REPLACEMENTS = {
    "sisanje": "Šišanje",
    "sredjivanje": "Sređivanje",
    "sminkanje": "Šminkanje",
}


def localized_service_name(name, language):
    if language != "sr":
        return name
    normalized = normalize_intent_text(name)
    return SERBIAN_SERVICE_DISPLAY_REPLACEMENTS.get(normalized, name)


def customer_memory_service_prompt(customer_memory):
    if not customer_memory:
        return ""
    return customer_memory.get("favorite_service") or customer_memory.get("last_service") or ""


def customer_memory_service_display(customer_memory, language):
    return localized_service_name(customer_memory_service_prompt(customer_memory), language)


def memory_prioritized_suggestions(tool_output):
    suggestions = list((tool_output or {}).get("suggested_slots", [])[:5])
    customer_memory = (tool_output or {}).get("customer_memory") or {}
    favorite_time = customer_memory.get("favorite_time") or ""
    if favorite_time:
        preferred = [slot for slot in suggestions if str(slot).startswith(favorite_time)]
        remaining = [slot for slot in suggestions if slot not in preferred]
        suggestions = preferred + remaining
    return ", ".join(suggestions[:3])


def local_greeting_part(language, business_client):
    local_hour = timezone.localtime(timezone.now(), client_timezone(business_client)).hour if business_client else timezone.localtime().hour
    if 3 <= local_hour < 10:
        part = "morning"
    elif 10 <= local_hour < 18:
        part = "day"
    else:
        part = "evening"

    if language == "sr":
        return {"morning": "Dobro jutro", "day": "Dobar dan", "evening": "Dobro vece"}[part]
    if language == "de":
        return {"morning": "Guten Morgen", "day": "Guten Tag", "evening": "Guten Abend"}[part]
    if language == "es":
        return {"morning": "Buenos dias", "day": "Buenas tardes", "evening": "Buenas noches"}[part]
    if language == "pt":
        return {"morning": "Bom dia", "day": "Boa tarde", "evening": "Boa noite"}[part]
    if language == "fr":
        return {"morning": "Bonjour", "day": "Bonjour", "evening": "Bonsoir"}[part]
    if language == "it":
        return {"morning": "Buongiorno", "day": "Buongiorno", "evening": "Buonasera"}[part]
    if language == "ru":
        return {"morning": "Dobroye utro", "day": "Dobryy den", "evening": "Dobryy vecher"}[part]
    return {"morning": "Good morning", "day": "Good afternoon", "evening": "Good evening"}[part]


def localized_greeting_response(language, business_client=None):
    business_name = str(business_client or "Kaleya").strip() if business_client else "Kaleya"
    greeting = local_greeting_part(language, business_client)
    if language == "sr":
        return f"{greeting}, {business_name}, izvolite."
    if language == "de":
        return f"{greeting}, {business_name}, bitte."
    if language == "es":
        return f"{greeting}, {business_name}, en que puedo ayudarle?"
    if language == "pt":
        return f"{greeting}, {business_name}, como posso ajudar?"
    if language == "fr":
        return f"{greeting}, {business_name}, je vous ecoute."
    if language == "it":
        return f"{greeting}, {business_name}, come posso aiutarla?"
    if language == "ru":
        return f"{greeting}, {business_name}, chem mogu pomoch?"
    return f"{greeting}, {business_name}, how can I help?"


def localized_gratitude_response(language):
    if language == "sr":
        return "Hvala vama, doviđenja."
    if language == "de":
        return "Danke Ihnen, auf Wiedersehen."
    if language == "es":
        return "Gracias a usted, hasta luego."
    if language == "pt":
        return "Obrigado, ate logo."
    if language == "fr":
        return "Merci a vous, au revoir."
    if language == "it":
        return "Grazie a lei, arrivederci."
    return "Thank you, goodbye."


def localized_see_you_response(language):
    if language == "sr":
        return "Vidimo se."
    if language == "de":
        return "Bis bald."
    if language == "es":
        return "Nos vemos."
    if language == "pt":
        return "Ate logo."
    if language == "fr":
        return "A bientot."
    if language == "it":
        return "A presto."
    return "See you."


SERBIAN_WEEKDAY_GENITIVE = {
    0: "ponedeljka",
    1: "utorka",
    2: "srede",
    3: "cetvrtka",
    4: "petka",
    5: "subote",
    6: "nedelje",
}


def sr_work_schedule_summary(business_client):
    work_start = business_client.work_start.strftime("%H:%M")
    work_end = business_client.work_end.strftime("%H:%M")
    rows = list(
        WorkingHours.objects.filter(business_client=business_client, staff_member__isnull=True).order_by("weekday")
    )
    if rows:
        open_days = [row.weekday for row in rows if not row.is_closed]
        if open_days == [0, 1, 2, 3, 4]:
            return f"od ponedeljka do petka od {work_start} do {work_end}"
        if open_days:
            day_names = ", ".join(SERBIAN_WEEKDAY_GENITIVE.get(day, str(day)) for day in open_days)
            return f"{day_names} od {work_start} do {work_end}"
    return f"od {work_start} do {work_end}"


def localized_no_available_booking_response(language, tool_output, business_client=None):
    date_value = tool_output.get("date") or ""
    requested_time = tool_output.get("requested_time") or tool_output.get("time") or ""
    next_slot = tool_output.get("next_available_slot") or {}
    if language == "sr":
        if tool_output.get("is_closed"):
            schedule = sr_work_schedule_summary(business_client) if business_client else "u podeseno radno vreme"
            return f"Izvinite, taj dan je neradan ({date_value}). Radno vreme je {schedule}."
        if next_slot:
            return f"Izvinjavam se, za {date_value} je sve zauzeto. Prvi slobodan termin je {next_slot.get('date')} u {next_slot.get('time')}."
        if requested_time:
            return f"Termin u {requested_time} nije slobodan za {date_value}. Napisite drugo vreme ili pitajte za slobodne termine tog dana."
        return f"Za {date_value} nema slobodnih termina. Napisite drugi datum."
    if language == "de":
        if tool_output.get("is_closed"):
            return f"An diesem Tag ist keine Buchung moeglich ({date_value}). Bitte nennen Sie ein anderes Datum."
        if requested_time:
            return f"Der Termin um {requested_time} ist fuer {date_value} nicht frei. Bitte nennen Sie eine andere Uhrzeit."
        return f"Fuer {date_value} gibt es keine freien Termine. Bitte nennen Sie ein anderes Datum."
    if tool_output.get("is_closed"):
        return f"That day is closed for booking ({date_value}). Please choose another date."
    if next_slot:
        return f"Sorry, {date_value} is fully booked. The first available slot is {next_slot.get('date')} at {next_slot.get('time')}."
    if requested_time:
        return f"The slot at {requested_time} is not available for {date_value}. Please choose another time or ask for free slots."
    return f"There are no available slots for {date_value}. Please choose another date."


def localized_time_preference_question(language):
    if language == "sr":
        return "Kada vam odgovara da proverim koji su slobodni termini?"
    if language == "de":
        return "Welche Uhrzeit wuerde Ihnen passen, damit ich freie Termine pruefen kann?"
    if language == "es":
        return "Que hora le viene bien para que revise los horarios libres?"
    if language == "pt":
        return "Que horario prefere para eu verificar os horarios livres?"
    if language == "fr":
        return "Quel horaire vous conviendrait pour que je verifie les creneaux disponibles?"
    if language == "it":
        return "Che orario preferisce, cosi controllo gli slot disponibili?"
    return "What time works for you so I can check the available slots?"


def localized_outside_work_hours_response(language, tool_output, business_client):
    suggestions = ", ".join((tool_output or {}).get("suggested_slots", [])[:3])
    work_start = (tool_output or {}).get("work_start") or business_client.work_start.strftime("%H:%M")
    work_end = (tool_output or {}).get("work_end") or business_client.work_end.strftime("%H:%M")
    if language == "sr":
        base = f"Izvinite, radno vreme je {sr_work_schedule_summary(business_client)}."
        if suggestions:
            return f"{base} Mogu da ponudim: {suggestions}."
        return base
    if language == "de":
        base = f"Entschuldigung, die Arbeitszeit ist von {work_start} bis {work_end}."
        if suggestions:
            return f"{base} Ich kann anbieten: {suggestions}."
        return base
    base = f"Sorry, working hours are {work_start} to {work_end}."
    if suggestions:
        return f"{base} I can offer: {suggestions}."
    return base


def service_clarifying_response(business_client, language, customer_memory=None):
    options = service_options_text(business_client, language=language)
    memory_service = customer_memory_service_display(customer_memory, language)
    if language == "sr":
        if memory_service:
            return f"Da li zelite opet {memory_service}? Ako ne, napisite koju uslugu zelite."
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
            return "Nisam sigurna da sam dobro razumela. Napišite mi malo konkretnije."
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
    waiting_statuses = {"needs_more_details", "needs_time", "needs_target", "needs_weekday", "time_unavailable", "failed"}
    state_status = "handoff" if intent_name == "support_handoff" else "open"
    if missing_fields or tool_status in waiting_statuses:
        state_status = "waiting_for_customer"
    if intent_name == "check_availability" and (
        "date" in (tool_output or {})
        or (tool_output or {}).get("requested_time")
        or (tool_output or {}).get("free_count", 0) > 0
    ):
        state_status = "waiting_for_customer"
    if tool_status in {"booked", "cancelled", "rescheduled"}:
        state_status = "completed"

    appointment_id = (tool_output or {}).get("appointment_id") or previous_state.get("last_appointment_id")
    appointment_date = (tool_output or {}).get("date") or previous_state.get("last_appointment_date")
    appointment_time = (tool_output or {}).get("time") or previous_state.get("last_appointment_time")
    pending_payload = {}
    if state_status == "waiting_for_customer":
        pending_payload = {key: value for key, value in (payload or {}).items() if not str(key).startswith("_")}
        if (tool_output or {}).get("date") and not pending_payload.get("date"):
            pending_payload["date"] = (tool_output or {}).get("date")
        if (tool_output or {}).get("requested_time") and not pending_payload.get("time"):
            pending_payload["time"] = (tool_output or {}).get("requested_time")
    state = {
        "status": state_status,
        "last_intent": intent_name,
        "last_confidence": float(confidence),
        "missing_fields": missing_fields or [],
        "pending_payload": json_safe(pending_payload),
        "last_tool_status": tool_status,
        "unknown_count": unknown_count,
    }
    if "free_count" in (tool_output or {}):
        state["last_free_count"] = int((tool_output or {}).get("free_count") or 0)
    if "is_closed" in (tool_output or {}):
        state["last_is_closed"] = bool((tool_output or {}).get("is_closed"))
    if "suggested_slots" in (tool_output or {}):
        state["last_suggested_slots"] = list((tool_output or {}).get("suggested_slots") or [])[:5]
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


def should_resume_previous_intent(intent_name, previous_state, text="", payload=None):
    if intent_name != "unknown":
        return False
    if not previous_state or previous_state.get("status") != "waiting_for_customer":
        return False
    if previous_state.get("last_tool_status") == "time_unavailable":
        payload = payload or {}
        return bool(
            has_fresh_date_or_time(text)
            or payload.get("_explicit_date")
            or payload.get("_explicit_time")
            or payload.get("_fresh_date_or_time")
        )
    return previous_state.get("last_intent") in RESUMABLE_INTENTS


def resume_previous_intent(previous_state):
    return previous_state.get("last_intent"), safe_float(previous_state.get("last_confidence"), 0.72)


def should_book_from_availability_followup(intent_name, previous_state, text, payload):
    if not previous_state or previous_state.get("last_intent") != "check_availability":
        return False
    if previous_state.get("status") not in {"open", "waiting_for_customer"}:
        return False
    if intent_name not in {"unknown", "book_appointment", "check_availability"}:
        return False
    return bool((payload or {}).get("time") or parse_requested_time(text))


def should_refine_availability_followup(intent_name, previous_state, text, payload):
    if not previous_state or previous_state.get("last_intent") != "check_availability":
        return False
    if previous_state.get("status") not in {"open", "waiting_for_customer"}:
        return False
    if intent_name not in {"unknown", "book_appointment", "check_availability"}:
        return False
    if not ((payload or {}).get("time") or parse_requested_time(text)):
        return False
    if contains_normalized_hint(text, BOOKING_CONFIRMATION_HINTS):
        return False
    return contains_normalized_hint(text, AVAILABILITY_REFINEMENT_HINTS)


def should_refine_reschedule_followup(intent_name, previous_state, text, payload):
    if not previous_state or previous_state.get("last_intent") != "reschedule_appointment":
        return False
    if previous_state.get("status") not in {"open", "waiting_for_customer"}:
        return False
    if previous_state.get("last_tool_status") not in {"needs_time", "time_unavailable"}:
        return False
    if intent_name not in {"unknown", "book_appointment", "check_availability", "reschedule_appointment"}:
        return False
    return bool(
        (payload or {}).get("_explicit_date")
        or (payload or {}).get("_explicit_time")
        or text_has_date_hint(text)
        or parse_requested_time(text)
        or parse_time_period_preference(text)
        or contains_normalized_hint(text, AVAILABILITY_REFINEMENT_HINTS)
        or contains_normalized_hint(text, AVAILABILITY_HINTS)
    )


def has_fresh_date_or_time(text):
    return bool(text_has_parseable_date(text) or parse_requested_time(text) or parse_time_period_preference(text))


def should_treat_bare_number_as_date(previous_state, text):
    if not previous_state or not parse_bare_day_of_month_date(text):
        return False
    missing_fields = set(previous_state.get("missing_fields") or [])
    if missing_fields.intersection({"date", "new_date"}):
        return True
    if previous_state.get("last_tool_status") == "time_unavailable":
        return bool(
            previous_state.get("last_is_closed")
            or int(previous_state.get("last_free_count") or 0) == 0
            or not previous_state.get("last_suggested_slots")
        )
    return False


def contextual_day_of_month_date(previous_state, text, business_client):
    if not previous_state:
        return None
    if parse_requested_time(text):
        return None
    normalized = normalize_intent_text(text)
    if not contains_normalized_hint(normalized, AVAILABILITY_HINTS):
        return None
    match = re.search(r"\b([1-9]|[12]\d|3[01])\b", normalized)
    if not match:
        return None
    return parse_bare_day_of_month_date(match.group(1), reference_date=client_local_today(business_client))


def next_day_from_previous_state(previous_state, text):
    if not previous_state:
        return None
    normalized = normalize_intent_text(text)
    if not any(phrase in normalized for phrase in ("sledeci dan", "sljedeci dan", "naredni dan", "dan posle", "next day")):
        return None
    previous_date = previous_state.get("last_appointment_date")
    if not previous_date:
        return None
    try:
        return date.fromisoformat(str(previous_date)) + timedelta(days=1)
    except ValueError:
        return None


def previous_suggested_time_from_text(previous_state, text):
    if not previous_state:
        return ""
    suggestions = set(previous_state.get("last_suggested_slots") or [])
    if not suggestions:
        return ""
    normalized = normalize_intent_text(text)
    for match in re.finditer(r"\b([01]?\d|2[0-3])\b", normalized):
        candidate = f"{int(match.group(1)):02d}:00"
        shifted = f"{int(match.group(1)) + 12:02d}:00" if int(match.group(1)) <= 11 else ""
        if candidate in suggestions:
            return candidate
        if shifted in suggestions:
            return shifted
    return ""


def previous_appointment_time_from_same_time_text(previous_state, text):
    if not previous_state:
        return ""
    normalized = normalize_intent_text(text)
    if not any(phrase in normalized for phrase in ("isto vreme", "isto vrijeme", "same time")):
        return ""
    return str(previous_state.get("last_appointment_time") or "")[:5]


def should_assume_booking_from_natural_text(intent_name, text, payload):
    if intent_name != "unknown":
        return False
    has_service = bool((payload or {}).get("service_id") or (payload or {}).get("service_hint"))
    has_date = bool((payload or {}).get("date"))
    has_time = bool((payload or {}).get("time"))
    has_natural_booking_hint = contains_normalized_hint(text, NATURAL_BOOKING_REQUEST_HINTS)
    if has_natural_booking_hint and has_service:
        return True
    if not has_fresh_date_or_time(text):
        return False
    return bool((has_date and has_time) or (has_service and (has_date or has_time)) or (has_natural_booking_hint and (has_date or has_time or has_service)))


def should_treat_as_reschedule_followup(intent_name, previous_state, text, payload):
    if not previous_state or previous_state.get("status") != "completed":
        return False
    if intent_name == "check_availability":
        return False
    if previous_state.get("last_intent") not in {"book_appointment", "reschedule_appointment"}:
        return False
    if not previous_state.get("last_appointment_id"):
        return False
    if intent_name not in AMBIGUOUS_COMPLETED_FOLLOWUP_INTENTS:
        return False
    if intent_name == "book_appointment" and contains_normalized_hint(text, BOOKING_ACTION_HINTS):
        return False
    if contains_normalized_hint(text, NATURAL_BOOKING_REQUEST_HINTS) and not (text_has_date_hint(text) or parse_requested_time(text)):
        return False
    return bool(payload.get("date") or payload.get("time") or text_has_date_hint(text) or parse_requested_time(text))


def should_use_last_appointment_date(intent_name, previous_state, text, payload):
    if intent_name != "reschedule_appointment":
        return False
    if not previous_state or not previous_state.get("last_appointment_date"):
        return False
    if payload.get("date") or text_has_date_hint(text):
        return False
    return bool(payload.get("time") or parse_requested_time(text))


def should_skip_ai_planner_for_simple_text(text, previous_state):
    return bool(
        is_greeting_text(text)
        or is_conversation_closing_text(text, previous_state)
        or is_customer_info_question(text, previous_state)
    )


def apply_confirmed_memory_service(payload, previous_state, text, customer_memory):
    payload = {**(payload or {})}
    if payload.get("service_id") or payload.get("service_hint"):
        return payload, False
    previous_missing = set((previous_state or {}).get("missing_fields") or [])
    if "service" not in previous_missing:
        return payload, False
    memory_service = customer_memory_service_prompt(customer_memory)
    if not memory_service or not is_short_confirmation_text(text):
        return payload, False
    payload["service_hint"] = memory_service
    return payload, True


def attach_last_appointment_to_payload(payload, previous_state):
    if not previous_state or not previous_state.get("last_appointment_id"):
        return payload
    payload = {**(payload or {})}
    payload.setdefault("appointment_id", previous_state["last_appointment_id"])
    return payload


def attach_last_appointment_date_to_payload(payload, previous_state):
    if not previous_state or not previous_state.get("last_appointment_date"):
        return payload
    payload = {**(payload or {})}
    payload.setdefault("date", previous_state["last_appointment_date"])
    return payload


def build_text_response(business_client, intent, tool_output):
    language = tool_output.get("response_language") or business_client.interface_language or business_client.language or "en"

    if tool_output.get("status") == "needs_more_details":
        return build_clarifying_response(business_client, intent, tool_output.get("missing_fields", []), tool_output)

    if intent == "check_availability":
        count = tool_output.get("free_count", 0)
        suggestions = ", ".join(tool_output.get("suggested_slots", [])[:3])
        requested_time = tool_output.get("requested_time") or ""
        if tool_output.get("status") == "needs_weekday":
            if language == "sr":
                return "Koji dan vam odgovara? Mogu da proverim ponedeljak, utorak, sredu, cetvrtak ili petak."
            return "Which day works for you? I can check Monday, Tuesday, Wednesday, Thursday or Friday."
        if tool_output.get("is_closed"):
            return localized_no_available_booking_response(language, tool_output, business_client=business_client)
        if requested_time:
            return localized_time_availability_response(
                language,
                requested_time,
                suggestions,
                bool(tool_output.get("requested_time_available")),
            )
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
            favorite_time = (tool_output.get("customer_memory") or {}).get("favorite_time") or ""
            if not tool_output.get("suggestion_time") and not favorite_time and tool_output.get("suggested_slots"):
                return localized_time_preference_question(language)
            if not suggestions and tool_output.get("next_available_slot"):
                return localized_no_available_booking_response(language, tool_output, business_client=business_client)
            return localized_status_response(
                BOOKING_RESPONSE_TEMPLATES,
                "needs_time",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
                suggestions=suggestions,
            )
        if status == "time_unavailable":
            if tool_output.get("is_outside_work_hours"):
                return localized_outside_work_hours_response(language, tool_output, business_client)
            if not suggestions:
                return localized_no_available_booking_response(language, tool_output, business_client=business_client)
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
            cancelled_count = int(tool_output.get("cancelled_count") or 1)
            if cancelled_count > 1:
                if language == "sr":
                    return f"Otkazala sam {cancelled_count} termina i oslobodila slotove. Javite se kada budete zeleli novi termin."
                if language == "de":
                    return f"Ich habe {cancelled_count} Termine abgesagt und die Zeitfenster freigegeben."
                return f"I cancelled {cancelled_count} appointments and released the slots."
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
            if not suggestions:
                return localized_no_available_booking_response(language, tool_output, business_client=business_client)
            return localized_status_response(
                RESCHEDULE_RESPONSE_TEMPLATES,
                "needs_time",
                language,
                date=tool_output.get("date"),
                suggestions=suggestions,
            )
        if tool_output.get("status") == "time_unavailable":
            if tool_output.get("is_outside_work_hours"):
                return localized_outside_work_hours_response(language, tool_output, business_client)
            if not suggestions:
                return localized_no_available_booking_response(language, tool_output, business_client=business_client)
            return localized_status_response(
                BOOKING_RESPONSE_TEMPLATES,
                "time_unavailable",
                language,
                date=tool_output.get("date"),
                time=tool_output.get("time"),
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
        if tool_output.get("status") == "greeting":
            return localized_greeting_response(language, business_client=business_client)
        if tool_output.get("status") == "see_you":
            return localized_see_you_response(language)
        if tool_output.get("status") == "gratitude":
            return localized_gratitude_response(language)
        if tool_output.get("status") == "customer_profile":
            return localized_customer_profile_response(language, tool_output.get("customer_profile") or {})
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
            return "Nisam sigurna da sam dobro razumela. Napišite mi malo konkretnije."
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
    incoming_payload = dict(payload or {})
    payload = incoming_payload
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
    if incoming_payload.get("date") or incoming_payload.get("time"):
        payload["_fresh_date_or_time"] = True
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

    skip_ai_for_simple_text = use_ai and should_skip_ai_planner_for_simple_text(text, previous_state)
    if skip_ai_for_simple_text:
        planner_raw_response = {"engine": "deterministic-small-talk", "skipped_ai": True}
    elif use_ai:
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
    next_day_date = next_day_from_previous_state(previous_state, text)
    if next_day_date:
        payload["date"] = next_day_date
        payload.pop("time", None)
        payload["_explicit_date"] = True
        planner_raw_response["next_day_from_previous_state"] = next_day_date.isoformat()
    contextual_date = contextual_day_of_month_date(previous_state, text, business_client)
    if contextual_date:
        if previous_state.get("pending_payload"):
            payload = merge_payloads(previous_state.get("pending_payload") or {}, payload)
        payload["date"] = contextual_date
        payload.pop("time", None)
        payload["_suppress_time_inference"] = True
        payload["_explicit_date"] = True
        planner_raw_response["contextual_day_of_month_date"] = contextual_date.isoformat()
    if next_day_date and previous_state.get("pending_payload"):
        payload = merge_payloads(previous_state.get("pending_payload") or {}, payload)
    suggested_time = previous_suggested_time_from_text(previous_state, text)
    if suggested_time and not payload.get("time"):
        payload["time"] = suggested_time
        payload["_explicit_time"] = True
        planner_raw_response["previous_suggested_time"] = suggested_time
    fresh_text_time = parse_requested_time(text)
    if fresh_text_time:
        payload["time"] = fresh_text_time
        payload["_explicit_time"] = True
        planner_raw_response["fresh_text_time"] = fresh_text_time
    elif parse_time_period_preference(text):
        payload.pop("time", None)
        planner_raw_response["fresh_time_period_preference"] = parse_time_period_preference(text)
    same_time = previous_appointment_time_from_same_time_text(previous_state, text)
    if same_time and not payload.get("time"):
        payload["time"] = same_time
        payload["_explicit_time"] = True
        planner_raw_response["used_same_time_from_previous_appointment"] = same_time
    if should_treat_bare_number_as_date(previous_state, text):
        bare_date = parse_bare_day_of_month_date(text, reference_date=client_local_today(business_client))
        if bare_date:
            payload["date"] = bare_date
            payload.pop("time", None)
            payload["_suppress_time_inference"] = True
            payload["_explicit_date"] = True
            planner_raw_response["bare_number_as_date"] = bare_date.isoformat()
    if is_abusive_text(text) and intent_name in {"unknown", "support_handoff", "business_info"}:
        intent_name = "support_handoff"
        confidence = max(confidence, 0.78)
        planner_raw_response["abusive_language"] = True
    elif is_conversation_closing_text(text, previous_state) and intent_name in {"unknown", "support_handoff"}:
        intent_name = "business_info"
        confidence = max(confidence, 0.86)
        if is_see_you_text(text):
            planner_raw_response["see_you"] = True
        else:
            planner_raw_response["gratitude"] = True
    elif is_greeting_text(text) and intent_name in {"unknown", "support_handoff"}:
        intent_name = "business_info"
        confidence = max(confidence, 0.86)
        planner_raw_response["greeting"] = True
    if is_customer_info_question(text, previous_state):
        intent_name = "business_info"
        confidence = max(confidence, 0.8)
        planner_raw_response["customer_profile_question"] = True
    if should_refine_reschedule_followup(intent_name, previous_state, text, payload):
        payload = merge_payloads(previous_state.get("pending_payload") or {}, payload)
        if parse_time_period_preference(text) and not parse_requested_time(text):
            payload.pop("time", None)
        intent_name = "reschedule_appointment"
        confidence = max(confidence, 0.78)
        planner_raw_response["refined_previous_reschedule"] = True
    elif should_refine_availability_followup(intent_name, previous_state, text, payload):
        payload = merge_payloads(previous_state.get("pending_payload") or {}, payload)
        intent_name = "check_availability"
        confidence = max(confidence, 0.78)
        planner_raw_response["refined_previous_availability"] = True
    elif should_book_from_availability_followup(intent_name, previous_state, text, payload):
        payload = merge_payloads(previous_state.get("pending_payload") or {}, payload)
        intent_name = "book_appointment"
        confidence = max(confidence, 0.76)
        planner_raw_response["resumed_from_availability"] = True
    elif should_resume_previous_intent(intent_name, previous_state, text, payload):
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
    current_customer_memory = customer_memory_context(customer)
    payload, confirmed_memory_service = apply_confirmed_memory_service(
        payload,
        previous_state,
        text,
        current_customer_memory,
    )
    if confirmed_memory_service:
        planner_raw_response["confirmed_memory_service"] = payload.get("service_hint", "")
    if should_use_last_appointment_date(intent_name, previous_state, text, payload):
        payload = attach_last_appointment_date_to_payload(payload, previous_state)
        planner_raw_response["used_last_appointment_date"] = True
    if planner_raw_response.get("bare_number_as_date"):
        payload.pop("time", None)
    if should_assume_booking_from_natural_text(intent_name, text, payload):
        intent_name = "book_appointment"
        confidence = max(confidence, 0.72)
        planner_raw_response["assumed_booking_from_natural_text"] = True
    preprocess = build_preprocess_context(
        business_client,
        text,
        customer=customer,
        payload=payload,
        channel=channel,
        language_fallback=conversation.language if conversation else "",
    )
    language = preprocess["language"]
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
        if planner_raw_response.get("greeting"):
            tool_output["status"] = "greeting"
        if planner_raw_response.get("see_you"):
            tool_output["status"] = "see_you"
        if planner_raw_response.get("gratitude"):
            tool_output["status"] = "gratitude"
        if planner_raw_response.get("customer_profile_question"):
            tool_output["status"] = "customer_profile"
            tool_output["customer_profile"] = customer_profile_payload(customer=customer, payload=payload)
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

    if use_ai and not skip_ai_for_simple_text and channel not in {"telegram", "whatsapp", "viber", "sms"}:
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
