from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView
from django.views.static import serve

from kaleya_config.dashboard_views import dashboard, dashboard_conversation_messages, dashboard_logout, forgot_password, setup_account
from kaleya_config.manifest_view import manifest_webmanifest


admin.site.site_header = "Kaleya"
admin.site.site_title = "Kaleya Admin"
admin.site.index_title = "Kaleya Admin"


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kaleya-backend"})


def status_check(request):
    import time
    from django.db import DatabaseError, connection

    result = {"status": "green", "components": {}}

    try:
        t0 = time.monotonic()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ms = round((time.monotonic() - t0) * 1000)
        result["components"]["database"] = {"status": "green", "latency_ms": db_ms}
    except DatabaseError as exc:
        result["components"]["database"] = {"status": "red", "error": str(exc)}
        result["status"] = "red"

    return JsonResponse(result)


def demo_phone_number(request):
    """Return a localized demo phone number based on visitor's country (CF-IPCountry header)."""
    import os
    country = (
        request.META.get("HTTP_CF_IPCOUNTRY") or
        request.headers.get("CF-IPCountry") or
        ""
    ).upper().strip()

    # Group countries to regions and pick the right env var
    # Env vars: DEMO_PHONE_US, DEMO_PHONE_GB, DEMO_PHONE_RS, DEMO_PHONE_DEFAULT
    region_map = {
        "US": ("DEMO_PHONE_US", "US"),
        "CA": ("DEMO_PHONE_US", "US"),
        "GB": ("DEMO_PHONE_GB", "GB"),
        "IE": ("DEMO_PHONE_GB", "GB"),
        "AU": ("DEMO_PHONE_GB", "GB"),
        "NZ": ("DEMO_PHONE_GB", "GB"),
        "RS": ("DEMO_PHONE_RS", "RS"),
        "HR": ("DEMO_PHONE_RS", "RS"),
        "BA": ("DEMO_PHONE_RS", "RS"),
        "ME": ("DEMO_PHONE_RS", "RS"),
        "SI": ("DEMO_PHONE_RS", "RS"),
        "MK": ("DEMO_PHONE_RS", "RS"),
    }

    env_key, region = region_map.get(country, ("DEMO_PHONE_DEFAULT", "INT"))
    number = os.environ.get(env_key) or os.environ.get("DEMO_PHONE_DEFAULT") or ""

    response = JsonResponse({"number": number, "region": region, "country": country})
    response["Cache-Control"] = "no-store"
    response["Access-Control-Allow-Origin"] = "*"
    return response


def no_cache_response(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def no_cache_static_serve(request, *args, **kwargs):
    return no_cache_response(serve(request, *args, **kwargs))


@method_decorator(ensure_csrf_cookie, name="dispatch")
class FrontendTemplateView(TemplateView):
    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        return no_cache_response(response)


urlpatterns = [
    path("", FrontendTemplateView.as_view(template_name="index.html"), name="frontend-index"),
    path("index.html", FrontendTemplateView.as_view(template_name="index.html"), name="frontend-index-html"),
    path("demo.html", FrontendTemplateView.as_view(template_name="demo.html"), name="frontend-demo"),
    path("god-mode.html", FrontendTemplateView.as_view(template_name="god-mode.html"), name="frontend-god-mode"),
    path("checkout.html", FrontendTemplateView.as_view(template_name="checkout.html"), name="frontend-checkout"),
    path("privacy.html", FrontendTemplateView.as_view(template_name="privacy.html"), name="frontend-privacy"),
    path("terms.html", FrontendTemplateView.as_view(template_name="terms.html"), name="frontend-terms"),
    path("register-basic.html", FrontendTemplateView.as_view(template_name="register-basic.html"), name="frontend-register-basic"),
    path("register-basic-yearly.html", FrontendTemplateView.as_view(template_name="register-basic-yearly.html"), name="frontend-register-basic-yearly"),
    path("register-pro.html", FrontendTemplateView.as_view(template_name="register-pro.html"), name="frontend-register-pro"),
    path("register-pro-yearly.html", FrontendTemplateView.as_view(template_name="register-pro-yearly.html"), name="frontend-register-pro-yearly"),
    path("register-business.html", FrontendTemplateView.as_view(template_name="register-business.html"), name="frontend-register-business"),
    path("register-business-plus.html", FrontendTemplateView.as_view(template_name="register-business-plus.html"), name="frontend-register-business-plus"),
    path("register-business-pro-plus.html", FrontendTemplateView.as_view(template_name="register-business-pro-plus.html"), name="frontend-register-business-pro-plus"),
    path("manifest.webmanifest", manifest_webmanifest, name="manifest-webmanifest"),
    path("sw.js", no_cache_static_serve, {"path": "sw.js", "document_root": settings.PROJECT_ROOT / "frontend"}),
    path("robots.txt", no_cache_static_serve, {"path": "robots.txt", "document_root": settings.PROJECT_ROOT / "frontend"}),
    path("sitemap.xml", no_cache_static_serve, {"path": "sitemap.xml", "document_root": settings.PROJECT_ROOT / "frontend"}),
    path("setup/", setup_account, name="account-setup"),
    path("forgot-password/", forgot_password, name="forgot-password"),
    path("dashboard/conversation/<int:conv_id>/messages/", dashboard_conversation_messages, name="dashboard-conv-messages"),
    path("dashboard/", dashboard, name="dashboard"),
    path("admin/", dashboard, name="kaleya-admin"),
    path("admin/logout/", dashboard_logout, name="kaleya-admin-logout"),
    path("admin/login/", lambda request: redirect("/?login=admin")),
    re_path(r"^admin/.+$", lambda request: redirect("/admin/")),
    path("django-admin/", admin.site.urls),
    path("healthz", health_check, name="healthz"),
    path("api/health/", health_check, name="health-check"),
    path("api/status/", status_check, name="status-check"),
    path("api/auth/", include("accounts.urls")),
    path("api/clients/", include("clients.urls")),
    path("api/staff-services/", include("staff_services.urls")),
    path("api/appointments/", include("appointments.urls")),
    path("api/communications/", include("communications.urls")),
    path("api/integrations/", include("integrations.urls")),
    path("api/ai/", include("ai_core.urls")),
    path("api/ai-agent/", include("ai_agent.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/support/", include("support.urls")),
    path("api/audit-log/", include("audit_log.urls")),
    path("api/demo-number/", demo_phone_number, name="demo-phone-number"),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", no_cache_static_serve, {"document_root": settings.PROJECT_ROOT / "frontend" / "assets"}),
        re_path(r"^logo\.png$", no_cache_static_serve, {"path": "logo.png", "document_root": settings.PROJECT_ROOT / "frontend"}),
        re_path(r"^media/(?P<path>.*)$", no_cache_static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
