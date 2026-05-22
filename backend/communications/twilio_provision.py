"""Twilio number provisioning for Kaleya tenants.

Each salon owner enters their business phone.  We detect the country,
purchase a local Twilio voice number, store it in IntegrationConnection,
and return call-forwarding instructions so the owner can redirect their
existing number to their new Kaleya AI number.

Russia (+7) is explicitly excluded — owner should contact us directly.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone as dt_tz

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Country detection — ordered longest prefix first to avoid false matches
# ---------------------------------------------------------------------------

# fmt: off
PHONE_PREFIX_TO_TWILIO_COUNTRY: list[tuple[str, str]] = [
    # ── Russia / CIS — NOT SUPPORTED (contact us) ──────────────────────────
    ("+7",    "RU"),   # Explicitly flagged — handled separately below

    # ── Americas ────────────────────────────────────────────────────────────
    # 10-digit +1 sub-codes first (Caribbean / territories)
    ("+1242", "BS"),   # Bahamas
    ("+1246", "BB"),   # Barbados
    ("+1264", "AI"),   # Anguilla
    ("+1268", "AG"),   # Antigua
    ("+1284", "VG"),   # British Virgin Islands
    ("+1340", "VI"),   # US Virgin Islands
    ("+1345", "KY"),   # Cayman Islands
    ("+1441", "BM"),   # Bermuda
    ("+1473", "GD"),   # Grenada
    ("+1649", "TC"),   # Turks and Caicos
    ("+1664", "MS"),   # Montserrat
    ("+1671", "GU"),   # Guam
    ("+1684", "AS"),   # American Samoa
    ("+1721", "SX"),   # Sint Maarten
    ("+1758", "LC"),   # Saint Lucia
    ("+1767", "DM"),   # Dominica
    ("+1784", "VC"),   # Saint Vincent
    ("+1787", "PR"),   # Puerto Rico
    ("+1809", "DO"),   # Dominican Republic
    ("+1868", "TT"),   # Trinidad and Tobago
    ("+1869", "KN"),   # Saint Kitts
    ("+1876", "JM"),   # Jamaica
    ("+1939", "PR"),   # Puerto Rico alternate
    # Generic +1 — US and Canada (Twilio handles area-code routing internally)
    ("+1",    "US"),

    ("+52",   "MX"),   # Mexico
    ("+54",   "AR"),   # Argentina
    ("+55",   "BR"),   # Brazil
    ("+56",   "CL"),   # Chile
    ("+57",   "CO"),   # Colombia
    ("+51",   "PE"),   # Peru
    ("+58",   "VE"),   # Venezuela
    ("+591",  "BO"),   # Bolivia
    ("+593",  "EC"),   # Ecuador
    ("+595",  "PY"),   # Paraguay
    ("+598",  "UY"),   # Uruguay
    ("+502",  "GT"),   # Guatemala
    ("+503",  "SV"),   # El Salvador
    ("+504",  "HN"),   # Honduras
    ("+505",  "NI"),   # Nicaragua
    ("+506",  "CR"),   # Costa Rica
    ("+507",  "PA"),   # Panama

    # ── Western Europe ───────────────────────────────────────────────────────
    ("+44",   "GB"),   # United Kingdom
    ("+49",   "DE"),   # Germany
    ("+33",   "FR"),   # France
    ("+39",   "IT"),   # Italy
    ("+34",   "ES"),   # Spain
    ("+351",  "PT"),   # Portugal
    ("+31",   "NL"),   # Netherlands
    ("+32",   "BE"),   # Belgium
    ("+41",   "CH"),   # Switzerland
    ("+43",   "AT"),   # Austria
    ("+353",  "IE"),   # Ireland
    ("+352",  "LU"),   # Luxembourg
    ("+45",   "DK"),   # Denmark
    ("+46",   "SE"),   # Sweden
    ("+47",   "NO"),   # Norway
    ("+358",  "FI"),   # Finland
    ("+354",  "IS"),   # Iceland

    # ── Central / Eastern Europe ─────────────────────────────────────────────
    ("+48",   "PL"),   # Poland
    ("+420",  "CZ"),   # Czech Republic
    ("+421",  "SK"),   # Slovakia
    ("+36",   "HU"),   # Hungary
    ("+40",   "RO"),   # Romania
    ("+359",  "BG"),   # Bulgaria
    ("+30",   "GR"),   # Greece
    ("+370",  "LT"),   # Lithuania
    ("+371",  "LV"),   # Latvia
    ("+372",  "EE"),   # Estonia

    # ── Balkans ──────────────────────────────────────────────────────────────
    ("+381",  "RS"),   # Serbia
    ("+382",  "ME"),   # Montenegro
    ("+385",  "HR"),   # Croatia
    ("+386",  "SI"),   # Slovenia
    ("+387",  "BA"),   # Bosnia & Herzegovina
    ("+389",  "MK"),   # North Macedonia

    # ── Middle East ──────────────────────────────────────────────────────────
    ("+971",  "AE"),   # UAE
    ("+966",  "SA"),   # Saudi Arabia
    ("+972",  "IL"),   # Israel
    ("+962",  "JO"),   # Jordan
    ("+961",  "LB"),   # Lebanon
    ("+965",  "KW"),   # Kuwait
    ("+973",  "BH"),   # Bahrain
    ("+974",  "QA"),   # Qatar
    ("+968",  "OM"),   # Oman

    # ── Asia-Pacific ─────────────────────────────────────────────────────────
    ("+61",   "AU"),   # Australia
    ("+64",   "NZ"),   # New Zealand
    ("+65",   "SG"),   # Singapore

    # ── Africa ───────────────────────────────────────────────────────────────
    ("+27",   "ZA"),   # South Africa
]
# fmt: on

# Countries where we cannot provision numbers — owner must contact us
UNSUPPORTED_COUNTRIES = {"RU", "CU", "KP", "IR", "SY"}

# Human-readable country names for UI messages
COUNTRY_NAMES: dict[str, str] = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom",
    "DE": "Germany", "FR": "France", "IT": "Italy", "ES": "Spain",
    "PT": "Portugal", "NL": "Netherlands", "BE": "Belgium", "CH": "Switzerland",
    "AT": "Austria", "IE": "Ireland", "LU": "Luxembourg", "DK": "Denmark",
    "SE": "Sweden", "NO": "Norway", "FI": "Finland", "IS": "Iceland",
    "PL": "Poland", "CZ": "Czech Republic", "SK": "Slovakia", "HU": "Hungary",
    "RO": "Romania", "BG": "Bulgaria", "GR": "Greece", "LT": "Lithuania",
    "LV": "Latvia", "EE": "Estonia", "RS": "Serbia", "ME": "Montenegro",
    "HR": "Croatia", "SI": "Slovenia", "BA": "Bosnia", "MK": "North Macedonia",
    "MX": "Mexico", "BR": "Brazil", "AR": "Argentina", "CO": "Colombia",
    "CL": "Chile", "PE": "Peru", "EC": "Ecuador", "UY": "Uruguay",
    "PY": "Paraguay", "BO": "Bolivia", "GT": "Guatemala", "CR": "Costa Rica",
    "PA": "Panama", "VE": "Venezuela", "DO": "Dominican Republic",
    "AE": "UAE", "SA": "Saudi Arabia", "IL": "Israel", "JO": "Jordan",
    "LB": "Lebanon", "KW": "Kuwait", "QA": "Qatar", "BH": "Bahrain",
    "AU": "Australia", "NZ": "New Zealand", "SG": "Singapore", "ZA": "South Africa",
    "RU": "Russia",
}


def normalize_phone(phone: str) -> str:
    """Strip spaces, dashes, brackets; ensure leading +."""
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone or "")
    if cleaned and not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def detect_country(phone: str) -> str | None:
    """Return Twilio 2-letter country code from phone number, or None."""
    normalized = normalize_phone(phone)
    for prefix, code in PHONE_PREFIX_TO_TWILIO_COUNTRY:
        if normalized.startswith(prefix):
            return code
    return None


def is_russia(phone: str) -> bool:
    return normalize_phone(phone).startswith("+7")


# ---------------------------------------------------------------------------
# Call-forwarding instruction templates
# ---------------------------------------------------------------------------

# GSM standard codes (work on most carriers globally, especially mobile)
# Some US landline carriers use *72 instead — we note this in instructions.
def forwarding_instructions(kaleya_number: str, country: str) -> dict:
    """Return forwarding codes and step-by-step instructions."""
    # US/CA AT&T / Verizon landlines use *72; mobile uses **21*...#
    # We show both variants for US.
    is_north_america = country in {"US", "CA"}

    gsm_forward_all   = f"**21*{kaleya_number}#"
    gsm_forward_busy  = f"**67*{kaleya_number}#"
    gsm_forward_noanswer = f"**61*{kaleya_number}#"
    gsm_cancel        = "##002#"

    atandt_forward    = f"*72{kaleya_number}"   # US AT&T / T-Mobile landlines

    steps_all = [
        f"Open your phone's dialer app",
        f"Dial: {gsm_forward_all}",
        f"Tap the call button and wait for confirmation",
        f"You will hear 'Forwarding activated' — done!",
    ]
    if is_north_america:
        steps_all.append(
            f"Note: If on AT&T/Verizon landline, use {atandt_forward} instead"
        )

    return {
        "kaleya_number": kaleya_number,
        "country": country,
        "country_name": COUNTRY_NAMES.get(country, country),
        # Forward ALL calls (recommended for AI receptionist)
        "code_forward_all": gsm_forward_all,
        # Forward only when busy
        "code_forward_busy": gsm_forward_busy,
        # Forward only when no answer (after N rings)
        "code_forward_noanswer": gsm_forward_noanswer,
        # Cancel all forwarding
        "code_cancel": gsm_cancel,
        # US landline alternative
        "code_us_landline": atandt_forward if is_north_america else None,
        # Step-by-step for "forward all"
        "steps": steps_all,
    }


# ---------------------------------------------------------------------------
# Twilio REST helpers (no SDK — raw urllib like the rest of the codebase)
# ---------------------------------------------------------------------------

class ProvisionError(Exception):
    """Raised when we cannot provision a number."""


def _twilio_auth_header() -> str:
    sid   = settings.KALEYA_TWILIO_ACCOUNT_SID
    token = settings.KALEYA_TWILIO_AUTH_TOKEN
    credentials = base64.b64encode(f"{sid}:{token}".encode()).decode()
    return f"Basic {credentials}"


def _twilio_post(path: str, data: dict) -> dict:
    sid = settings.KALEYA_TWILIO_ACCOUNT_SID
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/{path}"
    payload = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": _twilio_auth_header(),
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProvisionError(f"Twilio HTTP {exc.code}: {body}") from exc


def _twilio_get(path: str, params: dict | None = None) -> dict:
    sid = settings.KALEYA_TWILIO_ACCOUNT_SID
    qs  = ("?" + urllib.parse.urlencode(params)) if params else ""
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/{path}{qs}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": _twilio_auth_header()},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProvisionError(f"Twilio HTTP {exc.code}: {body}") from exc


# ---------------------------------------------------------------------------
# Main provisioning entry point
# ---------------------------------------------------------------------------

def provision_twilio_number(business_client) -> dict:
    """
    Buy a local Twilio number for *business_client*, configure its webhook,
    store it in IntegrationConnection, and return forwarding_instructions().

    Raises ProvisionError on failure (caller should catch and show to admin).
    """
    from integrations.models import IntegrationConnection

    phone   = (business_client.business_phone or "").strip()
    country = detect_country(phone)

    if is_russia(phone):
        raise ProvisionError(
            "RU:Russia is not supported via self-service. "
            "The salon owner should contact Kaleya support."
        )

    if not country:
        raise ProvisionError(
            f"Cannot detect country from number '{phone}'. "
            "Please enter the full international format, e.g. +14155550100."
        )

    if country in UNSUPPORTED_COUNTRIES:
        raise ProvisionError(
            f"Numbers for {COUNTRY_NAMES.get(country, country)} are not available "
            "via self-service. The salon owner should contact Kaleya support."
        )

    base_url  = getattr(settings, "KALEYA_PUBLIC_BASE_URL", "https://www.aikaleya.com").rstrip("/")
    voice_url = f"{base_url}/api/communications/voice/incoming/"
    sms_url   = f"{base_url}/api/communications/sms/incoming/"
    friendly  = f"Kaleya - {(business_client.public_name or business_client.name)[:50]}"

    common_params = {
        "VoiceUrl":          voice_url,
        "VoiceMethod":       "POST",
        "SmsUrl":            sms_url,
        "SmsMethod":         "POST",
        "FriendlyName":      friendly,
    }

    # Attempt in order: Local → Mobile → TollFree
    result    = None
    last_err  = ""
    for number_type in ("Local", "Mobile", "TollFree"):
        try:
            result = _twilio_post(
                f"IncomingPhoneNumbers/{country}/{number_type}.json",
                common_params,
            )
            break
        except ProvisionError as exc:
            last_err = str(exc)
            logger.warning(
                "Could not provision %s %s number: %s",
                country, number_type, exc,
            )

    if result is None:
        raise ProvisionError(
            f"Twilio has no available numbers for {COUNTRY_NAMES.get(country, country)} ({country}). "
            f"Last error: {last_err}. Contact Kaleya support to provision manually."
        )

    kaleya_number = result["phone_number"]
    twilio_sid    = result.get("sid", "")

    IntegrationConnection.objects.update_or_create(
        business_client=business_client,
        provider="phone",
        defaults={
            "public_number": kaleya_number,
            "enabled":       True,
            "status":        "connected",
            "config": {
                "twilio_number_sid":  twilio_sid,
                "country":            country,
                "provisioned_at":     datetime.now(dt_tz.utc).isoformat(),
                "voice_url":          voice_url,
            },
            "last_error": "",
        },
    )

    logger.info(
        "Provisioned Twilio number %s (%s) for client %s",
        kaleya_number, country, business_client.id,
    )

    return forwarding_instructions(kaleya_number, country)


def release_twilio_number(business_client) -> bool:
    """
    Release (delete) the Twilio number assigned to this client.
    Returns True if a number was released, False if none was assigned.
    """
    from integrations.models import IntegrationConnection

    connection = IntegrationConnection.objects.filter(
        business_client=business_client, provider="phone"
    ).first()

    if not connection or not connection.config.get("twilio_number_sid"):
        return False

    number_sid = connection.config["twilio_number_sid"]
    sid = settings.KALEYA_TWILIO_ACCOUNT_SID
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/IncomingPhoneNumbers/{number_sid}.json"

    req = urllib.request.Request(
        url,
        headers={"Authorization": _twilio_auth_header()},
        method="DELETE",
    )
    try:
        urllib.request.urlopen(req, timeout=20)
    except urllib.error.HTTPError as exc:
        logger.error("Failed to release Twilio number %s: %s", number_sid, exc)
        return False

    connection.public_number = ""
    connection.enabled       = False
    connection.status        = "draft"
    connection.config        = {}
    connection.save()

    logger.info("Released Twilio number %s for client %s", number_sid, business_client.id)
    return True
