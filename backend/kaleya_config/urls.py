from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve


def health_check(request):
    return JsonResponse({"status": "ok", "service": "kaleya-backend"})


urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="frontend-index"),
    path("demo.html", TemplateView.as_view(template_name="demo.html"), name="frontend-demo"),
    path("god-mode.html", TemplateView.as_view(template_name="god-mode.html"), name="frontend-god-mode"),
    path("privacy.html", TemplateView.as_view(template_name="privacy.html"), name="frontend-privacy"),
    path("terms.html", TemplateView.as_view(template_name="terms.html"), name="frontend-terms"),
    path("register-basic.html", TemplateView.as_view(template_name="register-basic.html"), name="frontend-register-basic"),
    path("register-pro.html", TemplateView.as_view(template_name="register-pro.html"), name="frontend-register-pro"),
    path("register-business.html", TemplateView.as_view(template_name="register-business.html"), name="frontend-register-business"),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/auth/", include("accounts.urls")),
    path("api/clients/", include("clients.urls")),
    path("api/appointments/", include("appointments.urls")),
    path("api/integrations/", include("integrations.urls")),
    path("api/ai/", include("ai_core.urls")),
    path("api/billing/", include("billing.urls")),
    path("api/support/", include("support.urls")),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r"^assets/(?P<path>.*)$", serve, {"document_root": settings.PROJECT_ROOT / "frontend" / "assets"}),
        re_path(r"^logo\.png$", serve, {"path": "logo.png", "document_root": settings.PROJECT_ROOT / "frontend"}),
    ]
