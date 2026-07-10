from django.apps import AppConfig


class AiCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_core"

    def ready(self):
        from django.db.models.signals import post_save, pre_delete
        from django.dispatch import receiver
        from django.utils import timezone

        from appointments.models import Appointment

        @receiver(pre_delete, sender=Appointment, dispatch_uid="ai_core_purge_alarms_on_delete")
        def purge_alarms_on_appointment_delete(sender, instance, **kwargs):
            # The FK is SET_NULL, so orphaned alarms would keep announcing a
            # deleted appointment — remove them together with the appointment.
            instance.alarm_events.all().delete()

        @receiver(post_save, sender=Appointment, dispatch_uid="ai_core_dismiss_alarms_on_cancel")
        def dismiss_alarms_on_appointment_cancel(sender, instance, **kwargs):
            if instance.status == "cancelled":
                instance.alarm_events.filter(dismissed_at__isnull=True).update(
                    dismissed_at=timezone.now()
                )
