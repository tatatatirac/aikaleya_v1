from django.utils import timezone

from notifications.models import NotificationJob, NotificationRule


DEFAULT_EVENT_CHANNELS = {
    "appointment_created": ("dashboard",),
    "appointment_changed": ("dashboard",),
    "appointment_cancelled": ("dashboard",),
    "support_needed": ("dashboard",),
}


def queue_notification_jobs_for_event(
    business_client,
    event,
    appointment=None,
    customer=None,
    language="en",
    payload=None,
):
    payload = payload or {}
    rules = list(
        NotificationRule.objects.filter(
            business_client=business_client,
            event=event,
            is_enabled=True,
        ).order_by("channel", "offset_minutes")
    )

    if not rules:
        rules = [
            NotificationRule(
                business_client=business_client,
                event=event,
                channel=channel,
                offset_minutes=0,
                language=language,
                template="",
                is_enabled=True,
            )
            for channel in DEFAULT_EVENT_CHANNELS.get(event, ("dashboard",))
        ]

    jobs = []
    now = timezone.now()
    for rule in rules:
        jobs.append(
            NotificationJob.objects.create(
                business_client=business_client,
                appointment=appointment,
                customer=customer,
                channel=rule.channel,
                scheduled_for=now + timezone.timedelta(minutes=rule.offset_minutes),
                payload={
                    "event": event,
                    "language": rule.language or language,
                    "template": rule.template,
                    "source": "kaleya_ai",
                    **payload,
                },
            )
        )
    return jobs
