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
    if any(normalize_lookup(keyword) in normalized for keyword in tomorrow_keywords):
        return base_date + timedelta(days=1)

    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", normalized)
    if iso_match:
        return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date()

    eu_match = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})\b", normalized)
    if eu_match:
        day, month, year = map(int, eu_match.groups())
        return date_cls(year, month, day)

    return base_date


def parse_requested_time(text, explicit_time=None):
    if explicit_time:
        return str(explicit_time)[:5]

    normalized = (text or "").lower().replace(".", ":")
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", normalized)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"

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

    prefixed = re.search(r"\b(?:u|at|um|alle|a las|às|a)\s+([01]?\d|2[0-3])\b", normalized)
    if prefixed:
        return f"{int(prefixed.group(1)):02d}:00"

    return ""


def as_time(value):
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value
    return datetime.strptime(str(value)[:5], "%H:%M").time()


def first_free_slots(business_client, target_date, duration_minutes=None, staff_member_id=None, limit=5):
    availability = availability_for_date(
        business_client,
        target_date,
        duration_minutes=duration_minutes,
        staff_member_id=staff_member_id,
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
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value.lower()).strip()


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

    if not inferred.get("time"):
        parsed_time = parse_requested_time(text)
        if parsed_time:
            inferred["time"] = parsed_time

    if not inferred.get("date") and any(
        keyword in normalize_lookup(text)
        for keyword in ("danas", "today", "hoy", "hoje", "sutra", "tomorrow", "mañana", "demain", "morgen")
    ):
        inferred["date"] = parse_requested_date(text, reference_date=client_local_today(business_client))

    return inferred


def eligible_staff_members(business_client, service=None, preferred_staff_member=None):
    if preferred_staff_member:
        return [preferred_staff_member]

    queryset = StaffMember.objects.filter(business_client=business_client, is_active=True)
    if service:
        queryset = queryset.filter(staff_services__service=service, staff_services__is_active=True)

    staff_members = list(queryset.distinct().order_by("full_name"))
    return staff_members or [None]


def format_suggested_slot(slot_time, staff_member=None):
    if staff_member:
        return f"{slot_time} - {staff_member.full_name}"
    return slot_time


def aggregate_staff_availability(business_client, target_date, duration_minutes, service=None, staff_member=None, limit=5):
    total_free = 0
    total_busy = 0
    is_closed = True
    suggested_details = []
    per_staff = []

    for candidate in eligible_staff_members(business_client, service=service, preferred_staff_member=staff_member):
        availability, slots = first_free_slots(
            business_client,
            target_date,
            duration_minutes=duration_minutes,
            staff_member_id=candidate.id if candidate else None,
            limit=limit,
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

    suggested_details = sorted(suggested_details, key=lambda item: (item["time"], item["staff_member"]))[:limit]
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
    }


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
        existing = Customer.objects.filter(business_client=business_client, phone=phone).first()
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
    payload = infer_payload_from_text(business_client, text, payload)
    target_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
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
        )
    availability, suggested_slots = first_free_slots(
        business_client,
        target_date,
        duration_minutes=duration,
        staff_member_id=staff_member.id if staff_member else None,
    )
    availability["suggested_slots"] = suggested_slots
    return availability


def book_appointment_tool(business_client, text="", customer=None, channel="web", payload=None):
    payload = infer_payload_from_text(business_client, text, payload)
    target_date = parse_requested_date(text, payload.get("date"), reference_date=client_local_today(business_client))
    requested_time = parse_requested_time(text, payload.get("time"))
    service = scoped_service(business_client, payload.get("service_id")) or resolve_service_by_hint(business_client, payload.get("service_hint"))
    staff_member = scoped_staff_member(business_client, payload.get("staff_member_id")) or resolve_staff_member_by_hint(business_client, payload.get("staff_hint"))
    duration = int(payload.get("duration_minutes") or (service.duration_minutes if service else business_client.slot_interval_minutes))
    aggregate_availability = aggregate_staff_availability(
        business_client,
        target_date,
        duration_minutes=duration,
        service=service,
        staff_member=staff_member,
    )
    suggested_slots = aggregate_availability["suggested_slots"]

    if not requested_time:
        return {
            "status": "needs_time",
            "date": target_date.isoformat(),
            "duration_minutes": duration,
            "suggested_slots": suggested_slots,
            "suggested_slots_detail": aggregate_availability["suggested_slots_detail"],
            "free_count": aggregate_availability["free_count"],
        }

    selected_staff_member = None
    requested_time_available = False
    for candidate in eligible_staff_members(business_client, service=service, preferred_staff_member=staff_member):
        availability, _ = first_free_slots(
            business_client,
            target_date,
            duration_minutes=duration,
            staff_member_id=candidate.id if candidate else None,
        )
        if requested_time in [slot["time"] for slot in availability["slots"] if slot["available"]]:
            selected_staff_member = candidate
            requested_time_available = True
            break

    if not requested_time_available:
        return {
            "status": "time_unavailable",
            "date": target_date.isoformat(),
            "requested_time": requested_time,
            "suggested_slots": suggested_slots,
            "suggested_slots_detail": aggregate_availability["suggested_slots_detail"],
            "free_count": aggregate_availability["free_count"],
        }

    customer = ensure_customer(business_client, customer=customer, payload={**payload, "channel": channel})
    appointment = Appointment(
        business_client=business_client,
        customer=customer,
        staff_member=selected_staff_member,
        service=service,
        title=payload.get("title") or ("AI booking request" if not customer else ""),
        status=Appointment.STATUS_CONFIRMED,
        date=target_date,
        start_time=as_time(requested_time),
        duration_minutes=duration,
        channel=channel,
        source="ai_agent",
        metadata={"created_by": "kaleya_ai", "input_text": text[:500]},
    )
    try:
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
        "customer": appointment.customer.full_name if appointment.customer else appointment.title,
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


def cancel_appointment_tool(business_client, text="", customer=None, payload=None):
    payload = payload or {}
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
    requested_time = parse_requested_time(text, payload.get("time"))
    if not requested_time:
        availability, suggested_slots = first_free_slots(
            business_client,
            target_date,
            duration_minutes=appointment.duration_minutes,
            staff_member_id=appointment.staff_member_id,
        )
        return {
            "status": "needs_time",
            "appointment_id": appointment.id,
            "date": target_date.isoformat(),
            "suggested_slots": suggested_slots,
            "free_count": availability["free_count"],
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
