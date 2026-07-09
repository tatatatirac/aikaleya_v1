"""Google Calendar OAuth start + callback endpoints."""

import logging
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from clients.utils import client_for_request
from integrations.google_calendar_service import (
    exchange_code_for_tokens,
    get_authorization_url,
    make_state_token,
    parse_state_token,
    save_tokens_to_integration,
    disconnect_calendar,
)
from integrations.models import IntegrationConnection
from clients.models import BusinessClient


logger = logging.getLogger(__name__)


@api_view(["POST", "GET"])
@permission_classes([IsAuthenticated])
def google_calendar_start(request):
    """Owner clicks 'Connect Google Calendar' → returns the auth URL.

    Frontend then redirects the browser to that URL.
    """
    business_client = client_for_request(request)
    if not business_client:
        return Response({"detail": "Klijent nije pronadjen."}, status=404)

    if not settings.KALEYA_GOOGLE_OAUTH_CLIENT_ID:
        return Response({"detail": "Google OAuth nije konfigurisan na serveru."}, status=500)

    state = make_state_token(business_client.id)
    # Persist state token so callback can verify it belongs to a valid tenant
    integration, _ = IntegrationConnection.objects.get_or_create(
        business_client=business_client,
        provider="google_calendar",
        defaults={"config": {}, "enabled": False, "status": "draft"},
    )
    config = dict(integration.config or {})
    config["oauth_state"] = state
    integration.config = config
    integration.save(update_fields=["config", "updated_at"])

    return Response({"authorize_url": get_authorization_url(business_client, state)})


@csrf_exempt
def google_calendar_callback(request):
    """Google posts back here with ?code=... after the owner consents."""
    error_param = request.GET.get("error")
    if error_param:
        return _redirect_to_dashboard(error=error_param)

    code = request.GET.get("code", "")
    state = request.GET.get("state", "")
    business_client_id, _nonce = parse_state_token(state)

    if not code or not business_client_id:
        return _redirect_to_dashboard(error="missing_code_or_state")

    business_client = BusinessClient.objects.filter(id=business_client_id).first()
    if not business_client:
        return _redirect_to_dashboard(error="unknown_tenant")

    # Verify state matches what we stored. A missing stored state means WE never
    # started this flow for the tenant — reject, otherwise a forged callback could
    # attach an attacker's Google account to a victim tenant.
    integration = IntegrationConnection.objects.filter(
        business_client=business_client, provider="google_calendar"
    ).first()
    expected_state = (integration.config or {}).get("oauth_state") if integration else None
    if not expected_state or expected_state != state:
        return _redirect_to_dashboard(error="invalid_state")

    # One-time use: clear the stored state immediately so the callback can't be replayed.
    config = dict(integration.config or {})
    config.pop("oauth_state", None)
    integration.config = config
    integration.save(update_fields=["config", "updated_at"])

    try:
        tokens = exchange_code_for_tokens(code)
    except Exception as exc:
        logger.warning("Google token exchange failed: %s", exc)
        return _redirect_to_dashboard(error="token_exchange_failed")

    if not tokens.get("refresh_token") and integration and (integration.config or {}).get("refresh_token"):
        # User had already consented and Google only sends refresh_token on first prompt — reuse old one
        tokens["refresh_token"] = (integration.config or {}).get("refresh_token")

    save_tokens_to_integration(business_client, tokens)

    return _redirect_to_dashboard(success="google_calendar_connected")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def google_calendar_disconnect(request):
    business_client = client_for_request(request)
    if not business_client:
        return Response({"detail": "Klijent nije pronadjen."}, status=404)
    disconnect_calendar(business_client)
    return Response({"ok": True})


def _redirect_to_dashboard(error: str | None = None, success: str | None = None) -> HttpResponse:
    """Send the browser back to the admin dashboard with a query-param flag."""
    if success:
        return HttpResponseRedirect(f"/dashboard/?gcal={quote(success)}")
    if error:
        return HttpResponseRedirect(f"/dashboard/?gcal-error={quote(error)}")
    return HttpResponseRedirect("/dashboard/")
