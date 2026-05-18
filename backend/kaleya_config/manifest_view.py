"""Dynamic PWA manifest — uses the logged-in tenant's logo if uploaded."""

from django.http import JsonResponse

from clients.utils import client_for_request


DEFAULT_LOGO_URL = "/logo.png"


def manifest_webmanifest(request):
    """Return a manifest.webmanifest tailored to the current tenant.

    - Anonymous visitors get the default Kaleya manifest.
    - Authenticated users with an uploaded logo get a manifest pointing
      to their logo so PWA install puts THEIR icon on the home screen.
    """
    base = {
        "name": "Kaleya",
        "short_name": "Kaleya",
        "description": "Kaleya AI receptionist and scheduling app.",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#020617",
        "theme_color": "#020617",
        "categories": ["business", "productivity"],
    }

    icon_url = DEFAULT_LOGO_URL
    icon_type = "image/png"

    if request.user.is_authenticated:
        try:
            client = client_for_request(request)
            if client and client.logo_image:
                icon_url = request.build_absolute_uri(client.logo_image.url)
                name_str = client.public_name or client.name
                if name_str:
                    base["name"] = name_str
                    base["short_name"] = name_str[:12]
                lowered = (client.logo_image.name or "").lower()
                if lowered.endswith(".jpg") or lowered.endswith(".jpeg"):
                    icon_type = "image/jpeg"
                elif lowered.endswith(".webp"):
                    icon_type = "image/webp"
                elif lowered.endswith(".svg"):
                    icon_type = "image/svg+xml"
        except Exception:
            # Never crash the manifest endpoint
            pass

    base["icons"] = [
        {"src": icon_url, "sizes": "192x192", "type": icon_type, "purpose": "any maskable"},
        {"src": icon_url, "sizes": "512x512", "type": icon_type, "purpose": "any maskable"},
    ]

    response = JsonResponse(base)
    response["Content-Type"] = "application/manifest+json"
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response
