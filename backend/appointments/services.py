from datetime import date as date_cls
from datetime import datetime, timedelta

from appointments.models import Appointment


ACTIVE_STATUSES = [
    Appointment.STATUS_CONFIRMED,
    Appointment.STATUS_MOVED,
    Appointment.STATUS_PENDING,
    Appointment.STATUS_BLOCKED,
]


def iter_work_slots(business_client, target_date, duration_minutes=None):
    duration = int(duration_minutes or business_client.slot_interval_minutes)
    step = int(business_client.slot_interval_minutes)
    current = datetime.combine(target_date, business_client.work_start)
    end = datetime.combine(target_date, business_client.work_end)

    while current + timedelta(minutes=duration) <= end:
        yield current.time()
        current += timedelta(minutes=step)


def appointment_overlaps(slot_start, duration_minutes, appointment):
    start_dt = datetime.combine(appointment.date, slot_start)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    other_start = datetime.combine(appointment.date, appointment.start_time)
    other_end = other_start + timedelta(minutes=appointment.duration_minutes)
    return start_dt < other_end and end_dt > other_start


def availability_for_date(business_client, target_date, duration_minutes=None, staff_member_id=None):
    duration = int(duration_minutes or business_client.slot_interval_minutes)
    appointments_query = Appointment.objects.select_related("customer", "staff_member", "service").filter(
        business_client=business_client,
        date=target_date,
    )
    if staff_member_id:
        appointments_query = appointments_query.filter(staff_member_id=staff_member_id)
    appointments = list(appointments_query.order_by("start_time"))
    active = [appointment for appointment in appointments if appointment.status in ACTIVE_STATUSES]

    slots = []
    for slot_time in iter_work_slots(business_client, target_date, duration):
        blocking_appointment = next(
            (appointment for appointment in active if appointment_overlaps(slot_time, duration, appointment)),
            None,
        )
        slots.append(
            {
                "time": slot_time.strftime("%H:%M"),
                "available": blocking_appointment is None,
                "appointment_id": blocking_appointment.id if blocking_appointment else None,
                "status": blocking_appointment.status if blocking_appointment else "available",
                "customer": blocking_appointment.customer.full_name if blocking_appointment and blocking_appointment.customer else "",
                "staff_member": blocking_appointment.staff_member.full_name if blocking_appointment and blocking_appointment.staff_member else "",
                "service": blocking_appointment.service.name if blocking_appointment and blocking_appointment.service else "",
            }
        )

    free_count = len([slot for slot in slots if slot["available"]])
    busy_count = len(slots) - free_count

    return {
        "date": target_date.isoformat(),
        "work_start": business_client.work_start.strftime("%H:%M"),
        "work_end": business_client.work_end.strftime("%H:%M"),
        "duration_minutes": duration,
        "staff_member_id": staff_member_id,
        "free_count": free_count,
        "busy_count": busy_count,
        "slots": slots,
    }


def today_availability_summary(business_client, staff_member_id=None):
    return availability_for_date(business_client, date_cls.today(), staff_member_id=staff_member_id)
