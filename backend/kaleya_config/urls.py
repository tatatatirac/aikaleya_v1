from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve

from kaleya_config.dashboard_views import dashboard, dashboard_logout


admin.site.site_header = "Kaleya"
admin.site.site_title = "Kaleya Admin"
admin.site.index_title = "Kaleya administracija"


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kaleya-backend"})


def no_cache_response(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def no_cache_static_serve(request, *args, **kwargs):
    return no_cache_response(serve(request, *args, **kwargs))


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
    path("register-pro.html", FrontendTemplateView.as_view(template_name="register-pro.html"), name="frontend-register-pro"),
    path("register-business.html", FrontendTemplateView.as_view(template_name="register-business.html"), name="frontend-register-business"),
    path("register-business-plus.html", FrontendTemplateView.as_view(template_name="register-business-plus.html"), name="frontend-register-business-plus"),
    path("register-business-pro-plus.html", FrontendTemplateView.as_view(template_name="register-business-pro-plus.html"), name="frontend-register-business-pro-plus"),
    path("manifest.webmanifest", no_cache_static_serve, {"path": "manifest.webmanifest", "document_root": settings.PROJECT_ROOT / "frontend"}),
    path("sw.js", no_cache_static_serve, {"path": "sw.js", "document_root": settings.PROJECT_ROOT / "frontend"}),
    path("dashboard/", dashboard, name="dashboard"),
    path("admin/", dashboard, name="kaleya-admin"),
    path("admin/logout/", dashboard_logout, name="kaleya-admin-logout"),
    path("admin/login/", lambda request: redirect("/?login=admin")),
    re_path(r"^admin/.+$", lambda request: redirect("/admin/")),
    path("django-admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
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
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", no_cache_static_serve, {"document_root": settings.PROJECT_ROOT / "frontend" / "assets"}),
        re_path(r"^logo\.png$", no_cache_static_serve, {"path": "logo.png", "document_root": settings.PROJECT_ROOT / "frontend"}),
        re_path(r"^media/(?P<path>.*)$", no_cache_static_serve, {"document_root": settings.MEDIA_ROOT}),
    ]
