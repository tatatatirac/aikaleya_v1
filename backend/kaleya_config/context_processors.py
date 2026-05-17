from django.conf import settings


def frontend_config(request):
    return {
        "sentry_dsn": getattr(settings, "SENTRY_DSN", "") or "",
    }
