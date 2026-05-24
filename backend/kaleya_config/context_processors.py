from django.conf import settings

# Maps Cloudflare CF-IPCountry code → Kaleya language code
# Cloudflare sends this header free on every request — no external API needed
_COUNTRY_LANG = {
    # Balkan (SR)
    "RS": "sr", "HR": "sr", "BA": "sr", "ME": "sr", "SI": "sr", "MK": "sr",
    # British English
    "GB": "en-gb", "IE": "en-gb",
    # French
    "FR": "fr", "BE": "fr", "LU": "fr", "MC": "fr",
    "SN": "fr", "CI": "fr", "CM": "fr", "ML": "fr", "BF": "fr",
    # Spanish
    "ES": "es", "MX": "es", "AR": "es", "CO": "es", "CL": "es",
    "PE": "es", "VE": "es", "EC": "es", "BO": "es", "UY": "es",
    "PY": "es", "GT": "es", "HN": "es", "SV": "es", "NI": "es",
    "CR": "es", "PA": "es", "CU": "es", "DO": "es", "PR": "es",
    # Portuguese
    "PT": "pt", "BR": "pt", "AO": "pt", "MZ": "pt", "CV": "pt",
    # Russian
    "RU": "ru", "BY": "ru", "KZ": "ru", "KG": "ru", "TJ": "ru",
    # Italian
    "IT": "it", "SM": "it", "VA": "it",
    # German
    "DE": "de", "AT": "de", "LI": "de", "CH": "de",
    # Default English-speaking countries → en
    "US": "en", "CA": "en", "AU": "en", "NZ": "en",
    "ZA": "en", "IN": "en", "SG": "en", "PH": "en", "NG": "en",
}


def frontend_config(request):
    country = request.META.get("HTTP_CF_IPCOUNTRY", "")
    geo_lang = _COUNTRY_LANG.get(country, "en")
    return {
        "sentry_dsn": getattr(settings, "SENTRY_DSN", "") or "",
        "geo_lang": geo_lang,
    }
