"""Sync appointments to Google Calendar via Django signals.

Mirror of appointment_sms.py but for GCal. On every Appointment save:
  - if the booking is active (confirmed/pending), create or update the event
  - if the booking transitioned to cancelled, delete the event
  - all event IDs persisted in Appointment.metadata.gcal_event_id
  - silent failure — never break appointment save if GCal API is unreachable
"""

import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from appointments.models import Appointment
from integrations.google_calendar_service import (
    create_event_for_appointment,
    delete_event,
    update_event_for_appointment,
)
from integrations.models import IntegrationConnection


logger = logging.getLogger(__name__)


def _tenant_has_calendar_integration(business_client) -> bool:
    return IntegrationConnection.objects.filter(
        business_client=business_client,
        provider="google_calendar",
        enabled=True,
        status="connected",
    ).exists()


@receiver(post_save, sender=Appointment)
def sync_appointment_to_gcal(sender, instance, created, **kwargs):
    """Push or update the matching Google Calendar event for this appointment."""
    business_client = instance.business_client
    if not _tenant_has_calendar_integration(business_client):
        return

    metadata = dict(instance.metadata or {})
    event_id = metadata.get("gcal_event_id")

    if instance.status == Appointment.STATUS_CANCELLED:
        if event_id:
            delete_event(business_client, event_id)
            metadata.pop("gcal_event_id", None)
            Appointment.objects.filter(pk=instance.pk).update(metadata=metadata)
        return

    if instance.status not in {Appointment.STATUS_CONFIRMED, Appointment.STATUS_PENDING, Appointment.STATUS_MOVED}:
        return

    try:
        if event_id:
            ok = update_event_for_appointment(business_client, instance, event_id)
            if not ok:
                # Token may have expired permanently — try creating fresh
                new_event_id = create_event_for_appointment(business_client, instance)
                if new_event_id:
                    metadata["gcal_event_id"] = new_event_id
                    Appointment.objects.filter(pk=instance.pk).update(metadata=metadata)
        else:
            new_event_id = create_event_for_appointment(business_client, instance)
            if new_event_id:
                metadata["gcal_event_id"] = new_event_id
                Appointment.objects.filter(pk=instance.pk).update(metadata=metadata)
    except Exception as exc:
        logger.warning("GCal sync failed for appt %s: %s", instance.id, exc)


@receiver(pre_delete, sender=Appointment)
def delete_gcal_event_on_appointment_delete(sender, instance, **kwargs):
    if not _tenant_has_calendar_integration(instance.business_client):
        return
    event_id = (instance.metadata or {}).get("gcal_event_id")
    if event_id:
        try:
            delete_event(instance.business_client, event_id)
        except Exception as exc:
            logger.warning("GCal delete on appt-delete failed for %s: %s", instance.id, exc)
