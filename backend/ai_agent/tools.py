import re
import unicodedata
from difflib import SequenceMatcher
from datetime import date as date_cls
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone

from appointments.models import Appointment, Customer
from appointments.services import availability_for_date, client_timezone
from clients.models import BusinessClient
from staff_services.models import Service, StaffMember


ACTIVE_STATUSES = (
    Appointment.STATUS_CONFIRMED,
    Appointment.STATUS_MOVED,
    Appointment.STATUS_PENDING,
)


DATE_KEYWORDS = {
    "today": ("danas", "today", "hoy", "hoje", "aujourd", "oggi", "сегодня", "heute"),
    "tomorrow": ("sutra", "tomorrow", "manana", "mañana", "amanha", "amanhã", "demain", "domani", "завтра", "morgen"),
}

DAY_AFTER_TOMORROW_KEYWORDS = (
    "prekosutra",
    "day after tomorrow",
    "after tomorrow",
    "pasado manana",
    "pasado manana",
    "apos amanha",
    "apres demain",
    "apres-demain",
    "dopodomani",
    "uebermorgen",
    "ubermorgen",
)

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


MONTH_NAME_NUMBERS = {
    "januar": 1,
    "januara": 1,
    "jan": 1,
    "februar": 2,
    "februara": 2,
    "feb": 2,
    "mart": 3,
    "marta": 3,
    "mar": 3,
    "april": 4,
    "aprila": 4,
    "apr": 4,
    "maj": 5,
    "maja": 5,
    "jun": 6,
    "juna": 6,
    "jul": 7,
    "jula": 7,
    "avgust": 8,
    "avgusta": 8,
    "august": 8,
    "augusta": 8,
    "septembar": 9,
    "septembra": 9,
    "sep": 9,
    "oktobar": 10,
    "oktobra": 10,
    "okt": 10,
    "novembar": 11,
    "novembra": 11,
    "nov": 11,
    "decembar": 12,
    "decembra": 12,
    "dec": 12,
}
WEEKDAY_NUMBERS = {
    "ponedeljak": 0,
    "ponedeljka": 0,
    "pon": 0,
    "monday": 0,
    "utorak": 1,
    "utorka": 1,
    "uto": 1,
    "tuesday": 1,
    "sreda": 2,
    "sredu": 2,
    "srede": 2,
    "sre": 2,
    "wednesday": 2,
    "cetvrtak": 3,
    "cetvrtka": 3,
    "ctvrtak": 3,
    "ctvrtka": 3,
    "cet": 3,
    "thursday": 3,
    "petak": 4,
    "petka": 4,
    "pet": 4,
    "friday": 4,
    "subota": 5,
    "subotu": 5,
    "subote": 5,
    "sub": 5,
    "saturday": 5,
    "nedelja": 6,
    "nedelju": 6,
    "nedelje": 6,
    "ned": 6,
    "sunday": 6,
}
MONTH_NAME_PATTERN = re.compile(
    r"\b(\d{1,2})(?:\.|-)?(?:og|tog|te|ti)?\s*("
    + "|".join(sorted(MONTH_NAME_NUMBERS, key=len, reverse=True))
    + r")\b"
)
DAY_OF_MONTH_PATTERN = re.compile(r"\b([1-9]|[12]\d|3[01])\s*(?:\.|og|tog|ti|te|st|nd|rd|th)\b")
WEEKDAY_PATTERN = re.compile(r"\b(" + "|".join(sorted(WEEKDAY_NUMBERS, key=len, reverse=True)) + r")\b")
SHORT_DATE_PATTERN = re.compile(r"\b([1-9]|[12]\d|3[01])[.\-/](0?[1-9]|1[0-2])\.?\b")
COMPACT_DATE_PATTERN = re.compile(r"\b(0?[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])\b")
THIS_WEEK_PHRASES = (
    "ove nedelje",
    "ovu nedelju",
    "ove sedmice",
    "ovu sedmicu",
    "this week",
)
NEXT_WEEK_PHRASES = (
    "sledece nedelje",
    "sledecu nedelju",
    "sledece sedmice",
    "sledecu sedmicu",
    "sljedece sedmice",
    "sljedecu sedmicu",
    "naredne nedelje",
    "narednu nedelju",
    "naredne sedmice",
    "narednu sedmicu",
    "next week",
)
WEEK_RANGE_PHRASES = THIS_WEEK_PHRASES + NEXT_WEEK_PHRASES
WEEK_CONTEXT_NOUNS = (
    "nedelje",
    "nedelju",
    "sedmice",
    "sedmicu",
    "week",
)
NEXT_WEEK_MODIFIERS = (
    "sledece",
    "sledecu",
    "sljedece",
    "sljedecu",
    "naredne",
    "narednu",
    "next",
)
THIS_WEEK_MODIFIERS = (
    "ove",
    "ovu",
    "this",
)
STRICT_NEXT_WEEKDAY_WORDS = (
    "sledeci",
    "sledeceg",
    "sljedeci",
    "sljedeceg",
    "naredni",
    "narednog",
    "iduci",
    "iduceg",
    "next",
)


PHONE_PATTERN = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{6,}\d)(?!\w)")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
CUSTOMER_NAME_PATTERNS = (
    re.compile(
        r"\b(?:for|za|para|pour|per|fur|für)\s+([^\d+@,.;:]{2,70})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:client|customer|klijent|musterija|mušterija|cliente|kunde)\s+([^\d+@,.;:]{2,70})",
        re.IGNORECASE,
    ),
)


def client_local_today(business_client):
    return timezone.localtime(timezone.now(), client_timezone(business_client)).date()


def next_date_for_day_of_month(base_date, day):
    for month_offset in range(13):
        month_index = base_date.month + month_offset - 1
        year = base_date.year + month_index // 12
        month = month_index % 12 + 1
        try:
            candidate = date_cls(year, month, day)
        except ValueError:
            continue
        if candidate >= base_date:
            return candidate
    return base_date


def next_date_for_weekday(base_date, weekday):
    days_ahead = (weekday - base_date.weekday()) % 7
    return base_date + timedelta(days=days_ahead)


def strict_next_date_for_weekday(base_date, weekday):
    days_ahead = (weekday - base_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return base_date + timedelta(days=days_ahead)


def week_start(base_date):
    return base_date - timedelta(days=base_date.weekday())


def make_date_in_current_or_next_year(base_date, day, month):
    candidate = date_cls(base_date.year, month, day)
    if candidate < base_date:
        candidate = date_cls(base_date.year + 1, month, day)
    return candidate


def contains_any_phrase(normalized, phrases):
    return any(phrase in normalized for phrase in phrases)


def token_matches_any(token, candidates):
    if token in candidates:
        return True
    if len(token) < 5:
        return False
    return any(SequenceMatcher(None, token, candidate).ratio() >= 0.84 for candidate in candidates)


def fuzzy_week_range_context(normalized):
    tokens = re.findall(r"\w+", normalized or "")
    for index, token in enumerate(tokens[:-1]):
        next_token = tokens[index + 1]
        if next_token not in WEEK_CONTEXT_NOUNS:
            continue
        phrase = f"{token} {next_token}"
        if token_matches_any(token, NEXT_WEEK_MODIFIERS):
            return "next_week", phrase
        if token_matches_any(token, THIS_WEEK_MODIFIERS):
            return "this_week", phrase
    return "", ""


def weekday_date_from_week_context(normalized, base_date):
    if contains_any_phrase(normalized, NEXT_WEEK_PHRASES):
        stripped = normalized
        for phrase in NEXT_WEEK_PHRASES:
            stripped = stripped.replace(phrase, " ")
        weekday_match = WEEKDAY_PATTERN.search(stripped)
        if not weekday_match:
            return None
        weekday = WEEKDAY_NUMBERS[weekday_match.group(1)]
        return week_start(base_date) + timedelta(days=7 + weekday)
    if contains_any_phrase(normalized, THIS_WEEK_PHRASES):
        stripped = normalized
        for phrase in THIS_WEEK_PHRASES:
            stripped = stripped.replace(phrase, " ")
        weekday_match = WEEKDAY_PATTERN.search(stripped)
        if not weekday_match:
            return None
        weekday = WEEKDAY_NUMBERS[weekday_match.group(1)]
        candidate = week_start(base_date) + timedelta(days=weekday)
        if candidate < base_date:
            candidate += timedelta(days=7)
        return candidate
    fuzzy_range, fuzzy_phrase = fuzzy_week_range_context(normalized)
    if fuzzy_range:
        stripped = normalized.replace(fuzzy_phrase, " ")
        weekday_match = WEEKDAY_PATTERN.search(stripped)
        if not weekday_match:
            return None
        weekday = WEEKDAY_NUMBERS[weekday_match.group(1)]
        if fuzzy_range == "next_week":
            return week_start(base_date) + timedelta(days=7 + weekday)
        candidate = week_start(base_date) + timedelta(days=weekday)
        if candidate < base_date:
            candidate += timedelta(days=7)
        return candidate
    weekday_match = WEEKDAY_PATTERN.search(normalized)
    if not weekday_match:
        return None
    weekday_word = weekday_match.group(1)
    weekday = WEEKDAY_NUMBERS[weekday_word]
    strict_next_pattern = r"\b(" + "|".join(STRICT_NEXT_WEEKDAY_WORDS) + r")\s+" + re.escape(weekday_word) + r"\b"
    if re.search(strict_next_pattern, normalized):
        return strict_next_date_for_weekday(base_date, weekday)
    return None


def week_range_request(text):
    normalized = normalize_lookup(text or "")
    matched_phrase = next((phrase for phrase in WEEK_RANGE_PHRASES if phrase in normalized), "")
    fuzzy_range = ""
    fuzzy_phrase = ""
    if not matched_phrase:
        fuzzy_range, fuzzy_phrase = fuzzy_week_range_context(normalized)
        matched_phrase = fuzzy_phrase
    if not matched_phrase:
        return ""
    stripped = normalized.replace(matched_phrase, " ")
    if WEEKDAY_PATTERN.search(stripped):
        return ""
    if fuzzy_range:
        return fuzzy_range
    return "next_week" if matched_phrase in NEXT_WEEK_PHRASES else "this_week"


def parse_requested_date(text, explicit_date=None, reference_date=None):
    base_date = reference_date or date_cls.today()
    if explicit_date:
        if isinstance(explicit_date, date_cls):
            return explicit_date
        return datetime.strptime(str(explicit_date), "%Y-%m-%d").date()

    normalized = normalize_lookup(text)
    today_keywords = DATE_KEYWORDS["today"] + ("сегодня",)
    tomorrow_keywords = DATE_KEYWORDS["tomorrow"] + ("mañana", "amanhã", "завтра")
    if any(normalize_lookup(keyword) in normalized for keyword in today_keywords):
        return base_date
    if any(normalize_lookup(keyword) in normalized for keyword in DAY_AFTER_TOMORROW_KEYWORDS):
        return base_date + timedelta(days=2)
    if any(normalize_lookup(keyword) in normalized for keyword in tomorrow_keywords):
        return base_date + timedelta(days=1)

    contextual_weekday = weekday_date_from_week_context(normalized, base_date)
    if contextual_weekday:
        return contextual_weekday

    requested_week_range = week_range_request(normalized)
    if requested_week_range == "next_week":
        return week_start(base_date) + timedelta(days=7)
    if requested_week_range == "this_week":
        return base_date

    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", normalized)
    if iso_match:
        return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date()

    eu_match = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})\b", normalized)
    if eu_match:
        day, month, year = map(int, eu_match.groups())
        return date_cls(year, month, day)

    short_date_match = SHORT_DATE_PATTERN.search(normalized)
    if short_date_match:
        day, month = map(int, short_date_match.groups())
        return make_date_in_current_or_next_year(base_date, day, month)

    month_name_match = MONTH_NAME_PATTERN.search(normalized)
    if month_name_match:
        day = int(month_name_match.group(1))
        month = MONTH_NAME_NUMBERS[month_name_match.group(2)]
        candidate = date_cls(base_date.year, month, day)
        if candidate < base_date:
            candidate = date_cls(base_date.year + 1, month, day)
        return candidate

    weekday_match = WEEKDAY_PATTERN.search(normalized)
    if weekday_match:
        return next_date_for_weekday(base_date, WEEKDAY_NUMBERS[weekday_match.group(1)])

    day_of_month_match = DAY_OF_MONTH_PATTERN.search(normalized)
    if day_of_month_match:
        return next_date_for_day_of_month(base_date, int(day_of_month_match.group(1)))

    compact_date_match = COMPACT_DATE_PATTERN.search(normalized)
    if compact_date_match:
        day, month = map(int, compact_date_match.groups())
        return make_date_in_current_or_next_year(base_date, day, month)

    return base_date


def parse_bare_day_of_month_date(text, reference_date=None):
    normalized = normalize_lookup(text)
    match = re.fullmatch(r"\s*([1-9]|[12]\d|3[01])\s*", normalized)
    if not match:
        return None
    return next_date_for_day_of_month(reference_date or date_cls.today(), int(match.group(1)))


def text_has_parseable_date(text):
    normalized = normalize_lookup(text)
    today_keywords = DATE_KEYWORDS["today"] + ("сегодня",)
    tomorrow_keywords = DATE_KEYWORDS["tomorrow"] + ("mañana", "amanhã", "завтра")
    return bool(
        any(normalize_lookup(keyword) in normalized for keyword in today_keywords)
        or any(normalize_lookup(keyword) in normalized for keyword in DAY_AFTER_TOMORROW_KEYWORDS)
        or any(normalize_lookup(keyword) in normalized for keyword in tomorrow_keywords)
        or week_range_request(normalized)
        or re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", normalized)
        or re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})\b", normalized)
        or SHORT_DATE_PATTERN.search(normalized)
        or MONTH_NAME_PATTERN.search(normalized)
        or WEEKDAY_PATTERN.search(normalized)
        or DAY_OF_MONTH_PATTERN.search(normalized)
        or COMPACT_DATE_PATTERN.search(normalized)
    )


def parse_requested_time(text, explicit_time=None):
    if explicit_time:
        return str(explicit_time)[:5]

    raw_normalized = normalize_lookup(text or "")
    if SHORT_DATE_PATTERN.search(raw_normalized) or COMPACT_DATE_PATTERN.search(raw_normalized):
        if not re.search(r"\b(?:u|at|um|alle|oko|around|about)\s*(?:[01]?\d|2[0-3])(?:[:]\d{2}|\s*h)\b", raw_normalized):
            return ""

    normalized = normalize_lookup((text or "").replace(".", ":"))
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", normalized)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"

    spaced_minutes = re.search(r"\b([01]?\d|2[0-3])\s+([0-5]\d)\b", normalized)
    if spaced_minutes:
        return f"{int(spaced_minutes.group(1)):02d}:{int(spaced_minutes.group(2)):02d}"

    compact_minutes = re.search(r"\b([01]?\d|2[0-3])([0-5]\d)\b", normalized)
    if compact_minutes:
        return f"{int(compact_minutes.group(1)):02d}:{int(compact_minutes.group(2)):02d}"

    spoken_minutes = re.search(r"\b([01]?\d|2[0-3])\s*(?:i|and)\s*([0-5]\d)\b", normalized)
    if spoken_minutes:
        return f"{int(spoken_minutes.group(1)):02d}:{int(spoken_minutes.group(2)):02d}"

    half_hour = re.search(r"\b(?:pola\s*|half\s+past\s+)([1-9]|1[0-9]|2[0-4])\b", normalized)
    if half_hour:
        hour = int(half_hour.group(1)) - 1
        if hour <= 0:
            hour += 12
        return f"{hour:02d}:30"

    ampm = re.search(r"\b([1-9]|1[0-2])\s*([ap])\.?\s*m\.?\b", normalized)
    if ampm:
        hour = int(ampm.group(1))
        if ampm.group(2) == "p" and hour != 12:
            hour += 12
        if ampm.group(2) == "a" and hour == 12:
            hour = 0
        return f"{hour:02d}:00"

    hour_suffix = re.search(r"\b([01]?\d|2[0-3])\s*(?:h|ч|час)\b", normalized)
    if hour_suffix:
        return f"{int(hour_suffix.group(1)):02d}:00"

    prefixed = re.search(r"\b(?:u|at|um|alle|a las|às|a)\s*([01]?\d|2[0-3])\b", normalized)
    if prefixed:
        return f"{int(prefixed.group(1)):02d}:00"

    approximate_hour = re.search(r"\b(?:oko|around|about|circa)\s*([01]?\d|2[0-3])\b", normalized)
    if approximate_hour:
        return f"{int(approximate_hour.group(1)):02d}:00"

    bare_hour = re.fullmatch(r"\s*([01]?\d|2[0-3])\s*", normalized)
    if bare_hour:
        return f"{int(bare_hour.group(1)):02d}:00"

    return ""


def explicit_today_request(text):
    normalized = normalize_lookup(text or "")
    today_keywords = DATE_KEYWORDS["today"] + ("ÑÐµÐ³Ð¾Ð´Ð½Ñ",)
    return any(normalize_lookup(keyword) in normalized for keyword in today_keywords)


def adjust_past_weekday_request(business_client, text, target_date, requested_time):
    if not WEEKDAY_PATTERN.search(normalize_lookup(text or "")):
        return target_date
    if explicit_today_request(text):
        return target_date
    local_now = timezone.localtime(timezone.now(), client_timezone(business_client))
    if target_date != local_now.date():
        return target_date
    if requested_time and as_time(requested_time) <= local_now.time():
        return target_date + timedelta(days=7)
    if not requested_time and local_now.time() >= business_client.work_end:
        return target_date + timedelta(days=7)
    return target_date


def parse_after_hour_time(text):
    """
    Detects 'posle 3', 'after 3', 'apres 15h', etc.
    Returns a suggestion_time 30 min past that hour so the slot search starts *after* it.
    E.g. 'posle 3' → '15:30', 'after 16' → '16:30'.
    Returns "" if no after-hour pattern is found.
    """
    normalized = normalize_lookup(text or "")
    after_match = re.search(
        r"\b(?:posle|poslije|after|apres|despues\s*de|dopo\s*le|nach)\s*([1-9]|1[0-9]|2[0-3])\b",
        normalized,
    )
    if not after_match:
        return ""
    hour = int(after_match.group(1))
    # Ambiguous small hours (1–8) in an "after" context are almost always PM
    if 1 <= hour <= 8:
        hour += 12
    return f"{hour:02d}:30"


def parse_time_period_preference(text, payload=None):
    payload = payload or {}
    if payload.get("time_preference"):
        return str(payload["time_preference"])[:5]
    normalized = normalize_lookup(text or "")
    if any(phrase in normalized for phrase in ("popodne", "poslepodne", "posle podne", "afternoon")):
        return "14:00"
    if any(phrase in normalized for phrase in ("prepodne", "pre podne", "ujutru", "morning")):
        return "10:00"
    if any(phrase in normalized for phrase in ("uvece", "vece", "evening")):
        return "18:00"
    # "posle 3" / "after 4" etc. — find first slot AFTER that hour
    after_time = parse_after_hour_time(text)
    if after_time:
        return after_time
    return ""


def parse_requested_time_from_payload(text, payload=None):
    payload = payload or {}
    if payload.get("_suppress_time_inference") and not payload.get("time"):
        return ""
    parsed_from_text = parse_requested_time(text)
    if parsed_from_text:
        return parsed_from_text
    # If text says "posle/after [hour]", the planner's exact time is wrong — suppress it
    # so the slot search starts just AFTER that hour instead of booking AT it.
    if parse_after_hour_time(text):
        return ""
    return parse_requested_time("", payload.get("time"))


def as_time(value):
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value
    return datetime.strptime(str(value)[:5], "%H:%M").time()


def normalize_requested_time_for_work_hours(business_client, requested_time):
    if not requested_time:
        return requested_time
    parsed = as_time(requested_time)
    shifted_hour = parsed.hour + 12
    if shifted_hour > 23:
        return requested_time
    shifted = parsed.replace(hour=shifted_hour)
    if parsed < business_client.work_start and shifted >= business_client.work_start:
        return shifted.strftime("%H:%M")
    return requested_time


def requested_time_outside_work_window(requested_time, work_start, work_end):
    if not requested_time:
        return False
    parsed = as_time(requested_time)
    start = as_time(work_start)
    end = as_time(work_end)
    return not (start <= parsed < end)


def first_free_slots(
    business_client,
    target_date,
    duration_minutes=None,
    staff_member_id=None,
    limit=5,
    exclude_past_slots=False,
):
    availability = availability_for_date(
        business_client,
        target_date,
        duration_minutes=duration_minutes,
        staff_member_id=staff_member_id,
        exclude_past_slots=exclude_past_slots,
    )
    slots = [slot["time"] for slot in availability["slots"] if slot["available"]]
    return availability, slots[:limit]


def scoped_staff_member(business_client, staff_member_id):
    if not staff_member_id:
        return None
    return StaffMember.objects.filter(id=staff_member_id, business_client=business_client, is_active=True).first()


def scoped_service(business_client, service_id):
    if not service_id:
        return None
    return Service.objects.filter(id=service_id, business_client=business_client, is_active=True).first()


def normalize_lookup(value):
    value = str(value or "").translate(SERBIAN_CYRILLIC_TRANSLITERATION)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("đ", "dj").replace("Đ", "dj")
    return re.sub(r"\s+", " ", value).strip()


def text_contains_phrase(text, phrase):
    normalized_text = f" {normalize_lookup(text)} "
    normalized_phrase = normalize_lookup(phrase)
    if not normalized_phrase:
        return False
    return f" {normalized_phrase} " in normalized_text or normalized_phrase in normalized_text


def fuzzy_phrase_score(text, phrase):
    normalized_text = normalize_lookup(text)
    normalized_phrase = normalize_lookup(phrase)
    if len(normalized_phrase) < 5:
        return 0
    tokens = [token for token in re.findall(r"\w+", normalized_text) if len(token) >= 5]
    candidates = tokens + ([normalized_text] if normalized_text else [])
    best_ratio = max((SequenceMatcher(None, normalized_phrase, candidate).ratio() for candidate in candidates), default=0)
    return len(normalized_phrase) if best_ratio >= 0.84 else 0


def extract_phone(text):
    match = PHONE_PATTERN.search(text or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def extract_email(text):
    match = EMAIL_PATTERN.search(text or "")
    return match.group(0).strip() if match else ""


def clean_customer_name_candidate(candidate):
    parts = re.split(r"\b(?:for|za|para|pour|per|fur|für)\b", candidate or "", flags=re.IGNORECASE)
    if len(parts) > 1:
        candidate = parts[-1]
    candidate = re.split(
        r"\b(?:phone|telefon|tel|email|mail|at|u|tomorrow|today|sutra|danas|service|usluga|on|na|za termin)\b",
        candidate or "",
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    candidate = re.sub(r"[\d+@].*$", "", candidate).strip(" ,.;:-")
    words = [word for word in re.split(r"\s+", candidate) if word]
    return " ".join(words[:4]).strip()


def looks_like_business_term(candidate, service=None, staff_member=None):
    normalized = normalize_lookup(candidate)
    if not normalized:
        return True
    if service and (
        text_contains_phrase(normalized, service.name)
        or text_contains_phrase(normalized, service.category)
    ):
        return True
    if staff_member and (
        text_contains_phrase(normalized, staff_member.full_name)
        or text_contains_phrase(normalized, staff_member.role_title)
    ):
        return True
    return normalized in {"termin", "appointment", "cita", "agendamento", "rendez", "service", "usluga"}


def infer_service_from_text(business_client, text):
    ranked = []
    for service in Service.objects.filter(business_client=business_client, is_active=True).order_by("name"):
        score = 0
        for phrase in (service.name, service.category, service.description):
            if phrase and text_contains_phrase(text, phrase):
                score += len(normalize_lookup(phrase))
            elif phrase:
                score += fuzzy_phrase_score(text, phrase)
        if score:
            ranked.append((score, service))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def infer_staff_from_text(business_client, text):
    ranked = []
    for staff_member in StaffMember.objects.filter(business_client=business_client, is_active=True).order_by("full_name"):
        score = 0
        for phrase in (staff_member.full_name, staff_member.role_title):
            if phrase and text_contains_phrase(text, phrase):
                score += len(normalize_lookup(phrase))
        if score:
            ranked.append((score, staff_member))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1] if ranked else None


def extract_customer_name(text, service=None, staff_member=None):
    for pattern in CUSTOMER_NAME_PATTERNS:
        for match in pattern.finditer(text or ""):
            candidate = clean_customer_name_candidate(match.group(1))
            if len(candidate) >= 2 and not looks_like_business_term(candidate, service=service, staff_member=staff_member):
                return candidate
    return ""


def infer_payload_from_text(business_client, text, payload=None):
    inferred = dict(payload or {})
    service = scoped_service(business_client, inferred.get("service_id")) or resolve_service_by_hint(
        business_client,
        inferred.get("service_hint"),
    )
    staff_member = scoped_staff_member(business_client, inferred.get("staff_member_id")) or resolve_staff_member_by_hint(
        business_client,
        inferred.get("staff_hint"),
    )

    if not service and not inferred.get("service_hint"):
        service = infer_service_from_text(business_client, text)
        if service:
            inferred["service_id"] = service.id
            inferred["service_hint"] = service.name

    if not staff_member and not inferred.get("staff_hint"):
        staff_member = infer_staff_from_text(business_client, text)
        if staff_member:
            inferred["staff_member_id"] = staff_member.id
            inferred["staff_hint"] = staff_member.full_name

    if not inferred.get("phone"):
        phone = extract_phone(text)
        if phone:
            inferred["phone"] = phone

    if not inferred.get("email"):
        email = extract_email(text)
        if email:
            inferred["email"] = email

    if not inferred.get("customer_name"):
        customer_name = extract_customer_name(text, service=service, staff_member=staff_member)
        if customer_name:
            inferred["customer_name"] = customer_name

    if not inferred.get("time") and not inferred.get("_suppress_time_inference"):
        parsed_time = parse_requested_time(text)
        if parsed_time:
            inferred["time"] = parsed_time

    if text_has_parseable_date(text):
        inferred["date"] = parse_requested_date(text, reference_date=client_local_today(business_client))

    return inferred


def eligible_staff_members(business_client, service=None, preferred_staff_member=None):
    if is_single_capacity_client(business_client):
        return [None]
    if preferred_staff_member:
        return [preferred_staff_member]

    queryset = StaffMember.objects.filter(business_client=business_client, is_active=True)
    if service:
        queryset = queryset.filter(staff_services__service=service, staff_services__is_active=True)

    staff_members = list(queryset.distinct().order_by("full_name"))
    return staff_members or [None]


def is_single_capacity_client(business_client):
    return getattr(business_client, "package", "") == BusinessClient.PACKAGE_BASIC


def format_suggested_slot(slot_time, staff_member=None):
    if staff_member:
        return f"{slot_time} - {staff_member.full_name}"
    return slot_time


def suggested_slot_time(label):
    return str(label or "").split(" - ", 1)[0]


def prioritize_suggested_slots(slot_labels, requested_time="", limit=5):
    labels = list(slot_labels or [])
    if not requested_time:
        return labels[:limit]
    target_minutes = as_time(requested_time).hour * 60 + as_time(requested_time).minute

    def sort_key(label):
        slot_time = as_time(suggested_slot_time(label))
        slot_minutes = slot_time.hour * 60 + slot_time.minute
        return (abs(slot_minutes - target_minutes), slot_minutes, str(label))

    return sorted(labels, key=sort_key)[:limit]


def prioritize_suggested_details(suggested_details, requested_time="", limit=5):
    details = list(suggested_details or [])
    if not requested_time:
        return sorted(details, key=lambda item: (item["time"], item["staff_member"]))[:limit]
    target_minutes = as_time(requested_time).hour * 60 + as_time(requested_time).minute

    def sort_key(item):
        slot_time = as_time(item["time"])
        slot_minutes = slot_time.hour * 60 + slot_time.minute
        return (abs(slot_minutes - target_minutes), slot_minutes, item["staff_member"])

    return sorted(details, key=sort_key)[:limit]


def aggregate_staff_availability(
    business_client,
    target_date,
    duration_minutes,
    service=None,
    staff_member=None,
    limit=5,
    requested_time="",
    exclude_past_slots=False,
):
    total_free = 0
    total_busy = 0
    is_closed = True
    suggested_details = []
    per_staff = []
    lookup_limit = 100 if requested_time else limit

    for candidate in eligible_staff_members(business_client, service=service, preferred_staff_member=staff_member):
        availability, slots = first_free_slots(
            business_client,
            target_date,
            duration_minutes=duration_minutes,
            staff_member_id=candidate.id if candidate else None,
            limit=lookup_limit,
            exclude_past_slots=exclude_past_slots,
        )
        total_free += availability["free_count"]
        total_busy += availability["busy_count"]
        is_closed = is_closed and availability["is_closed"]
        per_staff.append(
            {
                "staff_member_id": candidate.id if candidate else None,
                "staff_member": candidate.full_name if candidate else "",
                "free_count": availability["free_count"],
                "busy_count": availability["busy_count"],
                "is_closed": availability["is_closed"],
            }
        )
        for slot in slots:
            suggested_details.append(
                {
                    "time": slot,
                    "staff_member_id": candidate.id if candidate else None,
                    "staff_member": candidate.full_name if candidate else "",
                    "label": format_suggested_slot(slot, candidate),
                }
            )

    suggested_details = prioritize_suggested_details(suggested_details, requested_time=requested_time, limit=limit)
    return {
        "date": target_date.isoformat(),
        "work_start": business_client.work_start.strftime("%H:%M"),
        "work_end": business_client.work_end.strftime("%H:%M"),
        "duration_minutes": duration_minutes,
        "staff_member_id": staff_member.id if staff_member else None,
        "free_count": total_free,
        "busy_count": total_busy,
        "is_closed": is_closed,
        "slots": [],
        "per_staff": per_staff,
        "suggested_slots": [item["label"] for item in suggested_details],
        "suggested_slots_detail": suggested_details,
        "requested_time": requested_time or "",
        "requested_time_available": bool(requested_time and any(item["time"] == requested_time for item in suggested_details)),
    }


def next_available_slot_after(business_client, start_date, duration_minutes, service=None, staff_member=None, max_days=30):
    for day_offset in range(1, max_days + 1):
        candidate_date = start_date + timedelta(days=day_offset)
        availability = aggregate_staff_availability(
            business_client,
            candidate_date,
            duration_minutes=duration_minutes,
            service=service,
            staff_member=staff_member,
            limit=1,
            exclude_past_slots=True,
        )
        suggestions = availability.get("suggested_slots_detail") or []
        if suggestions:
            suggestion = suggestions[0]
            return {
                "date": candidate_date.isoformat(),
                "time": suggestion["time"],
                "label": suggestion["label"],
                "staff_member_id": suggestion["staff_member_id"],
                "staff_member": suggestion["staff_member"],
            }
    return {}


def resolve_staff_member_by_hint(business_client, hint):
    hint = (hint or "").strip()
    if not hint:
        return None
    return (
        StaffMember.objects.filter(business_client=business_client, is_active=True)
        .filter(Q(full_name__icontains=hint) | Q(role_title__icontains=hint))
        .order_by("full_name")
        .first()
    )


def resolve_service_by_hint(business_client, hint):
    hint = (hint or "").strip()
    if not hint:
        return None
    return (
        Service.objects.filter(business_client=business_client, is_active=True)
        .filter(Q(name__icontains=hint) | Q(category__icontains=hint) | Q(description__icontains=hint))
        .order_by("name")
        .first()
    )


def ensure_customer(business_client, customer=None, payload=None):
    if customer:
        return customer
    payload = payload or {}
    customer_id = payload.get("customer_id")
    if customer_id:
        return Customer.objects.filter(id=customer_id, business_client=business_client).first()

    name = (payload.get("customer_name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    email = (payload.get("email") or "").strip()
    if not any((name, phone, email)):
        return None

    if phone:
        phone_digits = re.sub(r"\D+", "", phone)
        phone_query = phone_digits[-6:] if len(phone_digits) >= 6 else phone
        existing = Customer.objects.filter(business_client=business_client, phone__icontains=phone_query).first()
        if existing:
            return existing

    if email:
        existing = Customer.objects.filter(business_client=business_client, email__iexact=email).first()
        if existing:
            return existing

    first_name, _, last_name = name.partition(" ")
    return Customer.objects.create(
        business_client=business_client,
        first_name=first_name or "AI",
        last_name=last_name or "Client",
        phone=phone,
        email=email,
        preferred_channel=payload.get("channel", "web"),
    )


def check_availability_tool(business_client, text="", payload=None):
    requested_week_range = week_range_request(text)
    payload = infer_payload_from_text(business_client, text, payload)
    if requested_week_range and not (payload or {}).get("_explicit_date"):
        return {
            "status": "needs_weekday",
            "date_range": requested_week_range,
            "free_count": 0,
            "busy_count": 0,
            "is_closed": False,
            "suggested_slots": [],
            "slots": [],
        }
    target_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
    requested_time = normalize_requested_time_for_work_hours(
        business_client,
        parse_requested_time_from_payload(text, payload),
    )
    if not requested_time:
        requested_time = normalize_requested_time_for_work_hours(
            business_client,
            parse_time_period_preference(text, payload),
        )
    target_date = adjust_past_weekday_request(business_client, text, target_date, requested_time)
    service = scoped_service(business_client, payload.get("service_id")) or resolve_service_by_hint(business_client, payload.get("service_hint"))
    staff_member = scoped_staff_member(business_client, payload.get("staff_member_id")) or resolve_staff_member_by_hint(business_client, payload.get("staff_hint"))
    duration = int(payload.get("duration_minutes") or (service.duration_minutes if service else business_client.slot_interval_minutes))
    if not staff_member and StaffMember.objects.filter(business_client=business_client, is_active=True).exists():
        return aggregate_staff_availability(
            business_client,
            target_date,
            duration_minutes=duration,
            service=service,
            staff_member=None,
            requested_time=requested_time,
            exclude_past_slots=True,
        )
    availability, suggested_slots = first_free_slots(
        business_client,
        target_date,
        duration_minutes=duration,
        staff_member_id=staff_member.id if staff_member else None,
        limit=100 if requested_time else 5,
        exclude_past_slots=True,
    )
    availability["suggested_slots"] = prioritize_suggested_slots(suggested_slots, requested_time=requested_time, limit=5)
    availability["requested_time"] = requested_time or ""
    availability["requested_time_available"] = bool(
        requested_time and requested_time in [slot["time"] for slot in availability["slots"] if slot["available"]]
    )
    return availability


def book_appointment_tool(business_client, text="", customer=None, channel="web", payload=None, is_test=False):
    payload = infer_payload_from_text(business_client, text, payload)
    target_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
    requested_time = normalize_requested_time_for_work_hours(
        business_client,
        parse_requested_time_from_payload(text, payload),
    )
    suggestion_time = requested_time or normalize_requested_time_for_work_hours(
        business_client,
        parse_time_period_preference(text, payload),
    )
    target_date = adjust_past_weekday_request(business_client, text, target_date, requested_time)
    service = scoped_service(business_client, payload.get("service_id")) or resolve_service_by_hint(business_client, payload.get("service_hint"))
    staff_hint = (payload.get("staff_hint") or "").strip()
    staff_member = scoped_staff_member(business_client, payload.get("staff_member_id")) or resolve_staff_member_by_hint(business_client, staff_hint)
    # If caller named a specific staff member who doesn't work here, tell them
    if staff_hint and not staff_member and not payload.get("staff_member_id"):
        available_staff = list(
            StaffMember.objects.filter(business_client=business_client, is_active=True)
            .order_by("full_name")
            .values_list("full_name", flat=True)[:6]
        )
        return {
            "status": "staff_not_found",
            "staff_hint": staff_hint,
            "available_staff": available_staff,
        }
    duration = int(payload.get("duration_minutes") or (service.duration_minutes if service else business_client.slot_interval_minutes))
    aggregate_availability = aggregate_staff_availability(
        business_client,
        target_date,
        duration_minutes=duration,
        service=service,
        staff_member=staff_member,
        requested_time=suggestion_time,
        exclude_past_slots=True,
    )
    suggested_slots = aggregate_availability["suggested_slots"]
    is_outside_work_hours = requested_time_outside_work_window(
        requested_time,
        aggregate_availability["work_start"],
        aggregate_availability["work_end"],
    )

    if not requested_time:
        next_available_slot = {}
        if not suggested_slots:
            next_available_slot = next_available_slot_after(
                business_client,
                target_date,
                duration,
                service=service,
                staff_member=staff_member,
            )
        return {
            "status": "needs_time",
            "date": target_date.isoformat(),
            "duration_minutes": duration,
            "suggested_slots": suggested_slots,
            "suggested_slots_detail": aggregate_availability["suggested_slots_detail"],
            "free_count": aggregate_availability["free_count"],
            "suggestion_time": suggestion_time,
            "next_available_slot": next_available_slot,
        }

    selected_staff_member = None
    requested_time_available = False
    for candidate in eligible_staff_members(business_client, service=service, preferred_staff_member=staff_member):
        availability, _ = first_free_slots(
            business_client,
            target_date,
            duration_minutes=duration,
            staff_member_id=candidate.id if candidate else None,
            exclude_past_slots=True,
        )
        if requested_time in [slot["time"] for slot in availability["slots"] if slot["available"]]:
            selected_staff_member = candidate
            requested_time_available = True
            break

    if not requested_time_available:
        next_available_slot = {}
        if not suggested_slots:
            next_available_slot = next_available_slot_after(
                business_client,
                target_date,
                duration,
                service=service,
                staff_member=staff_member,
            )
        return {
            "status": "time_unavailable",
            "date": target_date.isoformat(),
            "requested_time": requested_time,
            "suggestion_time": suggestion_time,
            "suggested_slots": suggested_slots,
            "suggested_slots_detail": aggregate_availability["suggested_slots_detail"],
            "free_count": aggregate_availability["free_count"],
            "is_closed": aggregate_availability["is_closed"],
            "is_outside_work_hours": is_outside_work_hours,
            "work_start": aggregate_availability["work_start"],
            "work_end": aggregate_availability["work_end"],
            "next_available_slot": next_available_slot,
        }

    customer = ensure_customer(business_client, customer=customer, payload={**payload, "channel": channel})
    base_title = payload.get("title") or ("AI booking request" if not customer else "")
    appointment = Appointment(
        business_client=business_client,
        customer=customer,
        staff_member=selected_staff_member,
        service=service,
        title=f"[TEST] {base_title}".strip() if is_test else base_title,
        status=Appointment.STATUS_CONFIRMED,
        date=target_date,
        start_time=as_time(requested_time),
        duration_minutes=duration,
        channel=channel,
        source="ai_agent_test" if is_test else "ai_agent",
        is_test=is_test,
        metadata={"created_by": "kaleya_ai_test" if is_test else "kaleya_ai", "input_text": text[:500]},
    )
    try:
        if is_test:
            # Test bookings skip validation — they must never block real slots
            appointment.save()
        else:
            appointment.full_clean()
            appointment.save()
    except DjangoValidationError as exc:
        return {
            "status": "failed",
            "date": target_date.isoformat(),
            "requested_time": requested_time,
            "error": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            "suggested_slots": suggested_slots,
        }

    return {
        "status": "booked",
        "appointment_id": appointment.id,
        "date": appointment.date.isoformat(),
        "time": appointment.start_time.strftime("%H:%M"),
        "duration_minutes": appointment.duration_minutes,
        "customer": appointment.customer.full_name if appointment.customer else "",
        "customer_identified": bool(appointment.customer and appointment.customer.full_name),
        "staff_member": appointment.staff_member.full_name if appointment.staff_member else "",
        "service": appointment.service.name if appointment.service else "",
    }


def find_target_appointment(business_client, customer=None, payload=None, text=""):
    payload = infer_payload_from_text(business_client, text, payload)
    appointment_id = payload.get("appointment_id")
    queryset = Appointment.objects.select_related("customer", "staff_member", "service").filter(
        business_client=business_client,
        status__in=ACTIVE_STATUSES,
    )
    if payload.get("staff_member_id"):
        queryset = queryset.filter(staff_member_id=payload["staff_member_id"])
    if appointment_id:
        return queryset.filter(id=appointment_id).first()
    if customer:
        return queryset.filter(customer=customer).order_by("date", "start_time").first()

    if payload.get("date"):
        queryset = queryset.filter(date=parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client)))
    if payload.get("time"):
        queryset = queryset.filter(start_time=as_time(payload.get("time")))
    if payload.get("phone"):
        phone_digits = re.sub(r"\D+", "", payload["phone"])
        phone_query = phone_digits[-6:] if len(phone_digits) >= 6 else payload["phone"]
        queryset = queryset.filter(customer__phone__icontains=phone_query)
    if payload.get("email"):
        queryset = queryset.filter(customer__email__iexact=payload["email"])

    query = (payload.get("customer_name") or "").strip()
    if query:
        tokens = [token for token in re.findall(r"[\wÀ-žА-Яа-я]+", query) if len(token) >= 2]
        if tokens:
            name_filter = Q()
            for token in tokens:
                name_filter |= Q(customer__first_name__icontains=token) | Q(customer__last_name__icontains=token) | Q(title__icontains=token)
            match = queryset.filter(name_filter).order_by("date", "start_time").first()
            if match:
                return match

    text_tokens = [token for token in re.findall(r"[\wÀ-žА-Яа-я]+", text or "") if len(token) >= 3]
    if text_tokens:
        loose_filter = Q()
        for token in text_tokens[:12]:
            loose_filter |= (
                Q(customer__first_name__icontains=token)
                | Q(customer__last_name__icontains=token)
                | Q(customer__phone__icontains=token)
                | Q(title__icontains=token)
            )
        return queryset.filter(loose_filter).order_by("date", "start_time").first()
    return queryset.order_by("date", "start_time").first()


def wants_to_cancel_all_appointments(text):
    normalized = normalize_lookup(text)
    return any(
        phrase in normalized
        for phrase in (
            "sve termine",
            "sve rezervacije",
            "sve zakazane",
            "all appointments",
            "all bookings",
            "all reservations",
        )
    )


def customer_from_cancel_payload(business_client, customer=None, payload=None):
    if customer:
        return customer
    payload = payload or {}
    if payload.get("customer_id"):
        found = Customer.objects.filter(id=payload["customer_id"], business_client=business_client).first()
        if found:
            return found
    phone = payload.get("phone") or ""
    if phone:
        phone_digits = re.sub(r"\D+", "", phone)
        phone_query = phone_digits[-6:] if len(phone_digits) >= 6 else phone
        found = Customer.objects.filter(business_client=business_client, phone__icontains=phone_query).first()
        if found:
            return found
    email = payload.get("email") or ""
    if email:
        return Customer.objects.filter(business_client=business_client, email__iexact=email).first()
    return None


def cancel_appointment_tool(business_client, text="", customer=None, payload=None):
    payload = payload or {}
    if wants_to_cancel_all_appointments(text):
        target_customer = customer_from_cancel_payload(business_client, customer=customer, payload=payload)
        if not target_customer:
            return {"status": "needs_target", "message": "customer_not_found_for_cancel_all"}
        appointments = list(
            Appointment.objects.filter(
                business_client=business_client,
                customer=target_customer,
                status__in=ACTIVE_STATUSES,
            ).order_by("date", "start_time")
        )
        if not appointments:
            return {"status": "needs_target", "message": "appointments_not_found_for_cancel_all"}
        for appointment in appointments:
            appointment.status = Appointment.STATUS_CANCELLED
            appointment.cancelled_reason = payload.get("reason") or payload.get("cancelled_reason") or "Cancelled by Kaleya AI"
            appointment.save(update_fields=["status", "cancelled_reason", "updated_at"])
        return {
            "status": "cancelled",
            "cancelled_count": len(appointments),
            "customer": target_customer.full_name,
        }

    appointment = find_target_appointment(business_client, customer=customer, payload=payload, text=text)
    if not appointment:
        return {"status": "needs_target", "message": "appointment_not_found"}
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.cancelled_reason = payload.get("reason") or payload.get("cancelled_reason") or "Cancelled by Kaleya AI"
    appointment.save(update_fields=["status", "cancelled_reason", "updated_at"])
    return {
        "status": "cancelled",
        "appointment_id": appointment.id,
        "date": appointment.date.isoformat(),
        "time": appointment.start_time.strftime("%H:%M"),
        "customer": appointment.customer.full_name if appointment.customer else appointment.title,
    }


def reschedule_appointment_tool(business_client, text="", customer=None, channel="web", payload=None):
    payload = infer_payload_from_text(business_client, text, payload)
    appointment = find_target_appointment(business_client, customer=customer, payload=payload, text=text)
    if not appointment:
        return {"status": "needs_target", "message": "appointment_not_found"}

    target_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
    requested_time = normalize_requested_time_for_work_hours(
        business_client,
        parse_requested_time_from_payload(text, payload),
    )
    suggestion_time = requested_time or normalize_requested_time_for_work_hours(
        business_client,
        parse_time_period_preference(text, payload),
    )
    if not requested_time:
        availability, suggested_slots = first_free_slots(
            business_client,
            target_date,
            duration_minutes=appointment.duration_minutes,
            staff_member_id=appointment.staff_member_id,
            limit=100 if suggestion_time else 5,
            exclude_past_slots=True,
        )
        suggested_slots = prioritize_suggested_slots(suggested_slots, requested_time=suggestion_time, limit=5)
        return {
            "status": "needs_time",
            "appointment_id": appointment.id,
            "date": target_date.isoformat(),
            "suggested_slots": suggested_slots,
            "free_count": availability["free_count"],
            "is_closed": availability["is_closed"],
            "work_start": availability["work_start"],
            "work_end": availability["work_end"],
        }

    availability, suggested_slots = first_free_slots(
        business_client,
        target_date,
        duration_minutes=appointment.duration_minutes,
        staff_member_id=appointment.staff_member_id,
        limit=100 if requested_time else 5,
        exclude_past_slots=True,
    )
    suggested_slots = prioritize_suggested_slots(suggested_slots, requested_time=requested_time, limit=5)
    is_outside_work_hours = requested_time_outside_work_window(
        requested_time,
        availability["work_start"],
        availability["work_end"],
    )
    requested_time_available = requested_time in [slot["time"] for slot in availability["slots"] if slot["available"]]
    if is_outside_work_hours or not requested_time_available:
        return {
            "status": "time_unavailable",
            "appointment_id": appointment.id,
            "date": target_date.isoformat(),
            "requested_time": requested_time,
            "suggestion_time": suggestion_time,
            "suggested_slots": suggested_slots,
            "free_count": availability["free_count"],
            "is_closed": availability["is_closed"],
            "is_outside_work_hours": is_outside_work_hours,
            "work_start": availability["work_start"],
            "work_end": availability["work_end"],
        }

    old_date = appointment.date
    old_time = appointment.start_time
    appointment.date = target_date
    appointment.start_time = as_time(requested_time)
    appointment.status = Appointment.STATUS_MOVED
    appointment.channel = channel
    try:
        appointment.full_clean()
        appointment.save()
    except DjangoValidationError as exc:
        appointment.date = old_date
        appointment.start_time = old_time
        return {
            "status": "failed",
            "appointment_id": appointment.id,
            "error": exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
        }

    return {
        "status": "rescheduled",
        "appointment_id": appointment.id,
        "old_date": old_date.isoformat(),
        "old_time": old_time.strftime("%H:%M"),
        "date": appointment.date.isoformat(),
        "time": appointment.start_time.strftime("%H:%M"),
    }
