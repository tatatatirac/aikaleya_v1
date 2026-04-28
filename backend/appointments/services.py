from datetime import date as date_cls
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Q
from django.utils import timezone

from appointments.models import Appointment
from staff_services.models import BlockedTime, WorkingHours


ACTIVE_STATUSES = [
    Appointment.STATUS_CONFIRMED,
    Appointment.STATUS_MOVED,
    Appointment.STATUS_PENDING,
    Appointment.STATUS_BLOCKED,
]


def client_timezone(business_client):
    try:
        return ZoneInfo(business_client.timezone or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def aware_client_datetime(business_client, target_date, target_time):
    value = datetime.combine(target_date, target_time)
    return timezone.make_aware(value, client_timezone(business_client))


def day_bounds(business_client, target_date):
    start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()), client_timezone(business_client))
    end = start + timedelta(days=1)
    return start, end


def effective_working_hours(business_client, target_date, staff_member_id=None):
    weekday = target_date.weekday()
    query = WorkingHours.objects.filter(business_client=business_client, weekday=weekday)
    working_hours = None

    if staff_member_id:
        working_hours = query.filter(staff_member_id=staff_member_id).first()

    if working_hours is None:
        working_hours = query.filter(staff_member__isnull=True).first()

    if working_hours:
        return {
            "start": working_hours.start_time,
            "end": working_hours.end_time,
            "is_closed": working_hours.is_closed,
        }

    return {
        "start": business_client.work_start,
        "end": business_client.work_end,
        "is_closed": False,
    }


def iter_work_slots(business_client, target_date, duration_minutes=None, staff_member_id=None):
    duration = int(duration_minutes or business_client.slot_interval_minutes)
    step = int(business_client.slot_interval_minutes)
    work_window = effective_working_hours(business_client, target_date, staff_member_id=staff_member_id)
    if work_window["is_closed"]:
        return

    current = datetime.combine(target_date, work_window["start"])
    end = datetime.combine(target_date, work_window["end"])

    while current + timedelta(minutes=duration) <= end:
        yield current.time()
        current += timedelta(minutes=step)


def appointment_overlaps(slot_start, duration_minutes, appointment):
    start_dt = datetime.combine(appointment.date, slot_start)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    other_start = datetime.combine(appointment.date, appointment.start_time)
    other_end = other_start + timedelta(minutes=appointment.duration_minutes)
    return start_dt < other_end and end_dt > other_start


def blocked_time_overlaps(business_client, target_date, slot_start, duration_minutes, blocked_time):
    start_dt = aware_client_datetime(business_client, target_date, slot_start)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    return start_dt < blocked_time.end_at and end_dt > blocked_time.start_at


def blocked_times_for_date(business_client, target_date, staff_member_id=None):
    start, end = day_bounds(business_client, target_date)
    query = BlockedTime.objects.select_related("staff_member").filter(
        business_client=business_client,
        start_at__lt=end,
        end_at__gt=start,
    )
    if staff_member_id:
        query = query.filter(Q(staff_member_id=staff_member_id) | Q(staff_member__isnull=True))
    return list(query.order_by("start_at"))


def availability_for_date(business_client, target_date, duration_minutes=None, staff_member_id=None):
    duration = int(duration_minutes or business_client.slot_interval_minutes)
    work_window = effective_working_hours(business_client, target_date, staff_member_id=staff_member_id)
    blocked_times = blocked_times_for_date(business_client, target_date, staff_member_id=staff_member_id)
    appointments_query = Appointment.objects.select_related("customer", "staff_member", "service").filter(
        business_client=business_client,
        date=target_date,
    )
    if staff_member_id:
        appointments_query = appointments_query.filter(staff_member_id=staff_member_id)
    appointments = list(appointments_query.order_by("start_time"))
    active = [appointment for appointment in appointments if appointment.status in ACTIVE_STATUSES]

    slots = []
    if work_window["is_closed"]:
        return {
            "date": target_date.isoformat(),
            "work_start": work_window["start"].strftime("%H:%M"),
            "work_end": work_window["end"].strftime("%H:%M"),
            "duration_minutes": duration,
            "staff_member_id": staff_member_id,
            "free_count": 0,
            "busy_count": 0,
            "is_closed": True,
            "slots": [],
        }

    for slot_time in iter_work_slots(business_client, target_date, duration, staff_member_id=staff_member_id):
        blocking_appointment = next(
            (appointment for appointment in active if appointment_overlaps(slot_time, duration, appointment)),
            None,
        )
        blocking_time = None if blocking_appointment else next(
            (blocked_time for blocked_time in blocked_times if blocked_time_overlaps(business_client, target_date, slot_time, duration, blocked_time)),
            None,
        )
        slots.append(
            {
                "time": slot_time.strftime("%H:%M"),
                "available": blocking_appointment is None and blocking_time is None,
                "appointment_id": blocking_appointment.id if blocking_appointment else None,
                "blocked_time_id": blocking_time.id if blocking_time else None,
                "status": blocking_appointment.status if blocking_appointment else ("blocked_time" if blocking_time else "available"),
                "customer": blocking_appointment.customer.full_name if blocking_appointment and blocking_appointment.customer else "",
                "staff_member": blocking_appointment.staff_member.full_name if blocking_appointment and blocking_appointment.staff_member else "",
                "service": blocking_appointment.service.name if blocking_appointment and blocking_appointment.service else "",
                "reason": blocking_time.reason if blocking_time else "",
            }
        )

    free_count = len([slot for slot in slots if slot["available"]])
    busy_count = len(slots) - free_count

    return {
        "date": target_date.isoformat(),
        "work_start": work_window["start"].strftime("%H:%M"),
        "work_end": work_window["end"].strftime("%H:%M"),
        "duration_minutes": duration,
        "staff_member_id": staff_member_id,
        "free_count": free_count,
        "busy_count": busy_count,
        "is_closed": False,
        "slots": slots,
    }


def today_availability_summary(business_client, staff_member_id=None):
    return availability_for_date(business_client, date_cls.today(), staff_member_id=staff_member_id)
