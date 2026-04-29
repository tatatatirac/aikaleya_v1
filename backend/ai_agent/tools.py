import re
from datetime import date as date_cls
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError

from appointments.models import Appointment, Customer
from appointments.services import availability_for_date
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


def parse_requested_date(text, explicit_date=None):
    if explicit_date:
        if isinstance(explicit_date, date_cls):
            return explicit_date
        return datetime.strptime(str(explicit_date), "%Y-%m-%d").date()

    normalized = (text or "").lower()
    if any(keyword in normalized for keyword in DATE_KEYWORDS["today"]):
        return date_cls.today()
    if any(keyword in normalized for keyword in DATE_KEYWORDS["tomorrow"]):
        return date_cls.today() + timedelta(days=1)

    iso_match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", normalized)
    if iso_match:
        return datetime.strptime(iso_match.group(0), "%Y-%m-%d").date()

    eu_match = re.search(r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](20\d{2})\b", normalized)
    if eu_match:
        day, month, year = map(int, eu_match.groups())
        return date_cls(year, month, day)

    return date_cls.today()


def parse_requested_time(text, explicit_time=None):
    if explicit_time:
        return str(explicit_time)[:5]

    normalized = (text or "").lower().replace(".", ":")
    match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", normalized)
    if match:
        return f"{int(match.group(1)):02d}:{int(match.group(2)):02d}"

    ampm = re.search(r"\b([1-9]|1[0-2])\s*(am|pm)\b", normalized)
    if ampm:
        hour = int(ampm.group(1))
        if ampm.group(2) == "pm" and hour != 12:
            hour += 12
        if ampm.group(2) == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:00"

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
    payload = payload or {}
    target_date = parse_requested_date(text, payload.get("date"))
    service = scoped_service(business_client, payload.get("service_id"))
    staff_member = scoped_staff_member(business_client, payload.get("staff_member_id"))
    duration = int(payload.get("duration_minutes") or (service.duration_minutes if service else business_client.slot_interval_minutes))
    availability, suggested_slots = first_free_slots(
        business_client,
        target_date,
        duration_minutes=duration,
        staff_member_id=staff_member.id if staff_member else None,
    )
    availability["suggested_slots"] = suggested_slots
    return availability


def book_appointment_tool(business_client, text="", customer=None, channel="web", payload=None):
    payload = payload or {}
    target_date = parse_requested_date(text, payload.get("date"))
    requested_time = parse_requested_time(text, payload.get("time"))
    service = scoped_service(business_client, payload.get("service_id"))
    staff_member = scoped_staff_member(business_client, payload.get("staff_member_id"))
    duration = int(payload.get("duration_minutes") or (service.duration_minutes if service else business_client.slot_interval_minutes))
    availability, suggested_slots = first_free_slots(
        business_client,
        target_date,
        duration_minutes=duration,
        staff_member_id=staff_member.id if staff_member else None,
    )

    if not requested_time:
        return {
            "status": "needs_time",
            "date": target_date.isoformat(),
            "duration_minutes": duration,
            "suggested_slots": suggested_slots,
            "free_count": availability["free_count"],
        }

    if requested_time not in [slot["time"] for slot in availability["slots"] if slot["available"]]:
        return {
            "status": "time_unavailable",
            "date": target_date.isoformat(),
            "requested_time": requested_time,
            "suggested_slots": suggested_slots,
            "free_count": availability["free_count"],
        }

    customer = ensure_customer(business_client, customer=customer, payload={**payload, "channel": channel})
    appointment = Appointment(
        business_client=business_client,
        customer=customer,
        staff_member=staff_member,
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
    payload = payload or {}
    appointment_id = payload.get("appointment_id")
    queryset = Appointment.objects.select_related("customer", "staff_member", "service").filter(
        business_client=business_client,
        status__in=ACTIVE_STATUSES,
    )
    if appointment_id:
        return queryset.filter(id=appointment_id).first()
    if customer:
        return queryset.filter(customer=customer).order_by("date", "start_time").first()

    query = (payload.get("customer_name") or payload.get("phone") or text or "").strip()
    if query:
        return (
            queryset.filter(
                customer__first_name__icontains=query
            ).order_by("date", "start_time").first()
            or queryset.filter(customer__last_name__icontains=query).order_by("date", "start_time").first()
            or queryset.filter(customer__phone__icontains=query).order_by("date", "start_time").first()
            or queryset.filter(title__icontains=query).order_by("date", "start_time").first()
        )
    return None


def cancel_appointment_tool(business_client, text="", customer=None, payload=None):
    appointment = find_target_appointment(business_client, customer=customer, payload=payload, text=text)
    if not appointment:
        return {"status": "needs_target", "message": "appointment_not_found"}
    appointment.status = Appointment.STATUS_CANCELLED
    appointment.cancelled_reason = "Cancelled by Kaleya AI"
    appointment.save(update_fields=["status", "cancelled_reason", "updated_at"])
    return {
        "status": "cancelled",
        "appointment_id": appointment.id,
        "date": appointment.date.isoformat(),
        "time": appointment.start_time.strftime("%H:%M"),
        "customer": appointment.customer.full_name if appointment.customer else appointment.title,
    }


def reschedule_appointment_tool(business_client, text="", customer=None, channel="web", payload=None):
    payload = payload or {}
    appointment = find_target_appointment(business_client, customer=customer, payload=payload, text=text)
    if not appointment:
        return {"status": "needs_target", "message": "appointment_not_found"}

    target_date = parse_requested_date(text, payload.get("date"))
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
