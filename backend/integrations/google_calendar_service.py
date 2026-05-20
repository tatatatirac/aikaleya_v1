"""Google Calendar OAuth + event sync for Kaleya tenants.

Per-tenant flow:
  1. Owner clicks "Connect Google Calendar" in client settings.
  2. We redirect to Google's consent screen with our scopes.
  3. Google redirects back to /api/integrations/google-calendar/callback/
     with ?code=... — we exchange that for access_token + refresh_token.
  4. refresh_token persisted in IntegrationConnection.config so we can
     keep minting access tokens without re-prompting the owner.

Once connected, every Appointment.save() that creates a new booking
fires a signal that pushes the event to the owner's primary calendar.
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib import error, parse, request

from django.conf import settings
from django.utils import timezone as dj_timezone

from clients.models import BusinessClient
from integrations.models import IntegrationConnection


logger = logging.getLogger(__name__)


AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"
SCOPES = "https://www.googleapis.com/auth/calendar.events"

PROVIDER = "google_calendar"


# ─── HTTP helpers ──────────────────────────────────────────────────────────

def _post_form(url: str, data: dict) -> dict:
    encoded = parse.urlencode(data).encode("utf-8")
    req = request.Request(url, data=encoded, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google OAuth HTTP {exc.code}: {body}") from exc


def _api_request(method: str, path: str, access_token: str, body: dict | None = None) -> dict:
    url = f"{CALENDAR_API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {access_token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Calendar API HTTP {exc.code}: {body_text}") from exc


# ─── OAuth ─────────────────────────────────────────────────────────────────

def get_authorization_url(business_client: BusinessClient, state: str) -> str:
    """Build the Google OAuth consent URL for this tenant."""
    if not settings.KALEYA_GOOGLE_OAUTH_CLIENT_ID:
        raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID not configured on server.")
    params = {
        "client_id": settings.KALEYA_GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.KALEYA_GOOGLE_OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",  # ensure we always get a refresh_token
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{parse.urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """POST authorization code → receive access_token + refresh_token."""
    return _post_form(TOKEN_URL, {
        "code": code,
        "client_id": settings.KALEYA_GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.KALEYA_GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.KALEYA_GOOGLE_OAUTH_REDIRECT_URI,
        "grant_type": "authorization_code",
    })


def refresh_access_token(refresh_token: str) -> dict:
    return _post_form(TOKEN_URL, {
        "client_id": settings.KALEYA_GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.KALEYA_GOOGLE_OAUTH_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })


def save_tokens_to_integration(business_client: BusinessClient, tokens: dict, email: str = "") -> IntegrationConnection:
    """Persist OAuth result on IntegrationConnection. Creates if missing."""
    refresh_token = tokens.get("refresh_token", "")
    access_token = tokens.get("access_token", "")
    expires_in = int(tokens.get("expires_in", 3600) or 3600)
    expires_at = (dj_timezone.now() + timedelta(seconds=expires_in - 60)).isoformat()

    integration, _ = IntegrationConnection.objects.get_or_create(
        business_client=business_client,
        provider=PROVIDER,
        defaults={"config": {}, "enabled": True, "status": "connected"},
    )
    config = dict(integration.config or {})
    # Keep existing refresh_token if Google didn't return a new one
    if refresh_token:
        config["refresh_token"] = refresh_token
    config["access_token"] = access_token
    config["expires_at"] = expires_at
    config["scope"] = tokens.get("scope", SCOPES)
    config["token_type"] = tokens.get("token_type", "Bearer")
    if email:
        config["email"] = email

    integration.config = config
    integration.enabled = True
    integration.status = "connected"
    integration.last_error = ""
    if email:
        integration.public_number = email  # repurpose field for display name
    integration.save()
    return integration


def get_active_access_token(business_client: BusinessClient) -> str | None:
    integration = IntegrationConnection.objects.filter(
        business_client=business_client, provider=PROVIDER, enabled=True
    ).first()
    if not integration:
        return None

    config = dict(integration.config or {})
    expires_at_str = config.get("expires_at")
    access_token = config.get("access_token")

    if access_token and expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at > dj_timezone.now():
                return access_token
        except Exception:
            pass

    refresh_token = config.get("refresh_token")
    if not refresh_token:
        return None
    try:
        new_tokens = refresh_access_token(refresh_token)
    except Exception as exc:
        logger.warning("Google token refresh failed for %s: %s", business_client, exc)
        integration.status = "error"
        integration.last_error = str(exc)[:500]
        integration.save(update_fields=["status", "last_error", "updated_at"])
        return None

    save_tokens_to_integration(business_client, new_tokens)
    return new_tokens.get("access_token")


def disconnect_calendar(business_client: BusinessClient) -> None:
    IntegrationConnection.objects.filter(
        business_client=business_client, provider=PROVIDER
    ).update(enabled=False, status="paused")


# ─── Calendar API ──────────────────────────────────────────────────────────

def _iso_with_offset(date_value, time_value, tz_name: str) -> str:
    """Build an ISO 8601 timestamp with offset for Google Calendar event."""
    naive = datetime.combine(date_value, time_value)
    try:
        from zoneinfo import ZoneInfo
        return naive.replace(tzinfo=ZoneInfo(tz_name)).isoformat()
    except Exception:
        return naive.replace(tzinfo=timezone.utc).isoformat()


def build_event_payload(business_client: BusinessClient, appointment) -> dict:
    """Translate an Appointment row into a Google Calendar event body."""
    tz_name = business_client.timezone or "Europe/Belgrade"
    start_iso = _iso_with_offset(appointment.date, appointment.start_time, tz_name)
    end_dt = (datetime.combine(appointment.date, appointment.start_time) +
              timedelta(minutes=appointment.duration_minutes))
    end_iso = _iso_with_offset(end_dt.date(), end_dt.time(), tz_name)

    customer = appointment.customer
    service = appointment.service
    staff = appointment.staff_member

    summary_bits = []
    if service and service.name:
        summary_bits.append(service.name)
    if customer and customer.full_name:
        summary_bits.append(customer.full_name)
    summary = " — ".join(summary_bits) or "Kaleya appointment"

    description_lines = ["Booked by Kaleya AI"]
    if customer and customer.phone:
        description_lines.append(f"Phone: {customer.phone}")
    if staff and getattr(staff, "name", ""):
        description_lines.append(f"Staff: {staff.name}")
    if appointment.notes:
        description_lines.append(f"Notes: {appointment.notes}")

    return {
        "summary": summary,
        "description": "\n".join(description_lines),
        "start": {"dateTime": start_iso, "timeZone": tz_name},
        "end": {"dateTime": end_iso, "timeZone": tz_name},
        "source": {"title": "Kaleya AI", "url": settings.KALEYA_PUBLIC_BASE_URL},
    }


def create_event_for_appointment(business_client: BusinessClient, appointment) -> str | None:
    """Push a new event to the tenant's primary calendar. Returns event ID."""
    access_token = get_active_access_token(business_client)
    if not access_token:
        return None
    payload = build_event_payload(business_client, appointment)
    try:
        result = _api_request("POST", "/calendars/primary/events", access_token, body=payload)
        return result.get("id")
    except Exception as exc:
        logger.warning("GCal create event failed for appt %s: %s", appointment.id, exc)
        return None


def update_event_for_appointment(business_client: BusinessClient, appointment, event_id: str) -> bool:
    access_token = get_active_access_token(business_client)
    if not access_token or not event_id:
        return False
    payload = build_event_payload(business_client, appointment)
    try:
        _api_request("PATCH", f"/calendars/primary/events/{parse.quote(event_id)}", access_token, body=payload)
        return True
    except Exception as exc:
        logger.warning("GCal update event %s failed: %s", event_id, exc)
        return False


def delete_event(business_client: BusinessClient, event_id: str) -> bool:
    access_token = get_active_access_token(business_client)
    if not access_token or not event_id:
        return False
    try:
        _api_request("DELETE", f"/calendars/primary/events/{parse.quote(event_id)}", access_token)
        return True
    except Exception as exc:
        logger.warning("GCal delete event %s failed: %s", event_id, exc)
        return False


# ─── OAuth state helpers ──────────────────────────────────────────────────

def make_state_token(business_client_id: int) -> str:
    """Sign a state value the callback can verify. Stored in Integration.config."""
    nonce = secrets.token_urlsafe(24)
    return f"{business_client_id}:{nonce}"


def parse_state_token(state: str) -> tuple[int | None, str | None]:
    if not state or ":" not in state:
        return None, None
    parts = state.split(":", 1)
    try:
        return int(parts[0]), parts[1]
    except ValueError:
        return None, None
