import os
from pathlib import Path

from dotenv import load_dotenv

try:
    import dj_database_url
except ImportError:
    dj_database_url = None


BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)).strip())
    except (TypeError, ValueError):
        return default


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]
if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "channels",
    "accounts",
    "clients",
    "staff_services",
    "appointments",
    "communications",
    "ai_core",
    "ai_agent",
    "integrations",
    "notifications",
    "billing",
    "support",
    "audit_log",
    "telnyx",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "kaleya_config.middleware.AdminSecurityHeadersMiddleware",
]

ROOT_URLCONF = "kaleya_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [PROJECT_ROOT / "frontend", BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "kaleya_config.context_processors.frontend_config",
            ],
        },
    },
]

WSGI_APPLICATION = "kaleya_config.wsgi.application"
ASGI_APPLICATION = "kaleya_config.asgi.application"

database_url = os.getenv("DATABASE_URL")
if database_url and dj_database_url:
    DATABASES = {"default": dj_database_url.parse(database_url, conn_max_age=600)}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")]},
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "kaleya-default-cache",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
STATICFILES_DIRS = [PROJECT_ROOT / "frontend" / "assets"]
MEDIA_URL = "media/"
MEDIA_ROOT = PROJECT_ROOT / "media"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DRF_ANON_THROTTLE_RATE", "80/hour"),
        "user": os.getenv("DRF_USER_THROTTLE_RATE", "1200/hour"),
        "auth": os.getenv("DRF_AUTH_THROTTLE_RATE", "5/min"),
        "public_browser_chat": os.getenv("DRF_PUBLIC_CHAT_THROTTLE_RATE", "4/hour"),
    },
    "PAGE_SIZE": 50,
}

CORS_ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS

# Conversation engine: "off" = legacy state machine, "on"/"all" = Claude agent for
# everyone, "client:<id>" = Claude agent only for that tenant (used for safe rollout).
KALEYA_AGENT_MODE = os.getenv("KALEYA_AGENT_MODE", "off")

KALEYA_AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
KALEYA_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
KALEYA_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
KALEYA_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
KALEYA_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
KALEYA_ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
KALEYA_ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "")

# Per-language voice IDs (optional overrides). If a language has no specific
# voice configured, we fall back to KALEYA_ELEVENLABS_VOICE_ID.
# Example .env:
#   ELEVENLABS_VOICE_ID_EN=EXAVITQu4vr4xnSDxMaL     (Sarah)
#   ELEVENLABS_VOICE_ID_SR=d3l4f3HgkE3P6Fo91lYA     (Ida — native Serbian)
KALEYA_ELEVENLABS_VOICE_BY_LANG = {
    "en":    os.getenv("ELEVENLABS_VOICE_ID_EN", ""),
    "en-gb": os.getenv("ELEVENLABS_VOICE_ID_EN_GB", ""),
    "es":    os.getenv("ELEVENLABS_VOICE_ID_ES", ""),
    "pt":    os.getenv("ELEVENLABS_VOICE_ID_PT", ""),
    "ru":    os.getenv("ELEVENLABS_VOICE_ID_RU", ""),
    "fr":    os.getenv("ELEVENLABS_VOICE_ID_FR", ""),
    "it":    os.getenv("ELEVENLABS_VOICE_ID_IT", ""),
    "de":    os.getenv("ELEVENLABS_VOICE_ID_DE", ""),
    "sr":    os.getenv("ELEVENLABS_VOICE_ID_SR", ""),
}

# Twilio (voice + SMS) — global fallback; per-tenant credentials live on IntegrationConnection
KALEYA_TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
KALEYA_TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
KALEYA_TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")  # +1XXXXXXXXXX
KALEYA_TWILIO_DRY_RUN = env_bool("TWILIO_DRY_RUN", DEBUG)
KALEYA_PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://www.aikaleya.com").rstrip("/")

# Comma-separated list of IPs that bypass the public browser-chat throttle.
# Useful for developer/owner testing without hitting the per-IP rate limit.
KALEYA_PUBLIC_CHAT_THROTTLE_WHITELIST = os.getenv("PUBLIC_CHAT_THROTTLE_WHITELIST", "")

# Google OAuth — used to authorize tenants' Google Calendars for appointment sync
KALEYA_GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
KALEYA_GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
KALEYA_GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI",
    f"{KALEYA_PUBLIC_BASE_URL}/api/integrations/google-calendar/callback/",
)

KALEYA_PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "manual").strip().lower()
KALEYA_PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL", "http://127.0.0.1:8000/?payment=success")
KALEYA_PAYMENT_CANCEL_URL = os.getenv("PAYMENT_CANCEL_URL", "http://127.0.0.1:8000/?payment=cancel")

KALEYA_LEMONSQUEEZY_API_BASE = os.getenv("LEMONSQUEEZY_API_BASE", "https://api.lemonsqueezy.com").rstrip("/")
KALEYA_LEMONSQUEEZY_API_KEY = os.getenv("LEMONSQUEEZY_API_KEY", "")
KALEYA_LEMONSQUEEZY_STORE_ID = os.getenv("LEMONSQUEEZY_STORE_ID", "")
KALEYA_LEMONSQUEEZY_WEBHOOK_SECRET = os.getenv("LEMONSQUEEZY_WEBHOOK_SECRET", "")
KALEYA_LEMONSQUEEZY_TEST_MODE = env_bool("LEMONSQUEEZY_TEST_MODE", True)
KALEYA_LEMONSQUEEZY_VARIANT_IDS = {
    "basic": os.getenv("LEMONSQUEEZY_VARIANT_BASIC", ""),
    "basic_yearly": os.getenv("LEMONSQUEEZY_VARIANT_BASIC_YEARLY", ""),
    "pro": os.getenv("LEMONSQUEEZY_VARIANT_PRO", ""),
    "pro_yearly": os.getenv("LEMONSQUEEZY_VARIANT_PRO_YEARLY", ""),
    "business": os.getenv("LEMONSQUEEZY_VARIANT_BUSINESS", ""),
    "business_yearly": os.getenv("LEMONSQUEEZY_VARIANT_BUSINESS_YEARLY", ""),
    "business_plus": os.getenv("LEMONSQUEEZY_VARIANT_BUSINESS_PLUS", ""),
    "business_plus_yearly": os.getenv("LEMONSQUEEZY_VARIANT_BUSINESS_PLUS_YEARLY", ""),
    "business_pro_plus": os.getenv("LEMONSQUEEZY_VARIANT_BUSINESS_PRO_PLUS", ""),
}

KALEYA_PAYPAL_ENVIRONMENT = os.getenv("PAYPAL_ENVIRONMENT", "sandbox").strip().lower()
KALEYA_PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID", "")
KALEYA_PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET", "")
KALEYA_PAYPAL_WEBHOOK_ID = os.getenv("PAYPAL_WEBHOOK_ID", "")
KALEYA_PAYPAL_PLAN_IDS = {
    "basic": os.getenv("PAYPAL_PLAN_BASIC", ""),
    "pro": os.getenv("PAYPAL_PLAN_PRO", ""),
    "business": os.getenv("PAYPAL_PLAN_BUSINESS", ""),
    "business_plus": os.getenv("PAYPAL_PLAN_BUSINESS_PLUS", ""),
    "business_pro_plus": os.getenv("PAYPAL_PLAN_BUSINESS_PRO_PLUS", ""),
}
# ── Telnyx ──────────────────────────────────────────────────────────────────────
KALEYA_TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
KALEYA_TELNYX_VOICE_APP_ID = os.getenv("TELNYX_VOICE_APP_ID", "")
KALEYA_TELNYX_OUTBOUND_VOICE_PROFILE_ID = os.getenv("TELNYX_OUTBOUND_VOICE_PROFILE_ID", "")
KALEYA_TELNYX_MESSAGING_PROFILE_ID = os.getenv("TELNYX_MESSAGING_PROFILE_ID", "")
KALEYA_TELNYX_TEST_NUMBER_USA = os.getenv("TELNYX_TEST_NUMBER_USA", "")
KALEYA_TELNYX_TEST_NUMBER_CA = os.getenv("TELNYX_TEST_NUMBER_CA", "")
KALEYA_PUBLIC_URL = os.getenv("PUBLIC_URL", "https://aikaleya.com")

KALEYA_STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
KALEYA_STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
KALEYA_STRIPE_PRICE_IDS = {
    "basic": os.getenv("STRIPE_PRICE_BASIC", ""),
    "pro": os.getenv("STRIPE_PRICE_PRO", ""),
    "business": os.getenv("STRIPE_PRICE_BUSINESS", ""),
    "business_plus": os.getenv("STRIPE_PRICE_BUSINESS_PLUS", ""),
    "business_pro_plus": os.getenv("STRIPE_PRICE_BUSINESS_PRO_PLUS", ""),
}

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Kaleya <no-reply@aikaleya.com>")
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)

DATA_BACKUP_DIR = Path(os.getenv("DATA_BACKUP_DIR", PROJECT_ROOT / "backups"))

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")
DJANGO_ENV = os.getenv("DJANGO_ENV", "development" if DEBUG else "production")
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_DSN and not DEBUG:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        def _sentry_before_send(event, hint):
            # Drop internet background-noise exceptions: bot scanners send bogus
            # Host headers and probe paths, which would otherwise flood Sentry's
            # quota and bury real errors. DisallowedHost is a SuspiciousOperation.
            exc_info = hint.get("exc_info")
            if exc_info:
                from django.core.exceptions import SuspiciousOperation
                from django.http import Http404
                if isinstance(exc_info[1], (SuspiciousOperation, Http404)):
                    return None
            return event

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.1,
            send_default_pii=False,
            environment=DJANGO_ENV,
            before_send=_sentry_before_send,
        )
    except ImportError:
        pass

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "ai_agent": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}
