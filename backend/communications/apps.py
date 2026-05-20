from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "communications"
    verbose_name = "Komunikacije"

    def ready(self):
        # Wire signal handlers (appointment confirmation SMS, calendar sync, etc.)
        from communications import appointment_sms  # noqa: F401
        from communications import appointment_calendar  # noqa: F401
