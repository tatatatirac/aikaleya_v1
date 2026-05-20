from django.urls import path
from rest_framework.routers import DefaultRouter

from integrations.google_calendar_views import (
    google_calendar_callback,
    google_calendar_disconnect,
    google_calendar_start,
)
from integrations.views import (
    IntegrationConnectionViewSet,
    TelegramWebhookAPIView,
    WhatsAppWebhookAPIView,
    ViberWebhookAPIView,
)


router = DefaultRouter()
router.register("connections", IntegrationConnectionViewSet, basename="integration-connection")

urlpatterns = router.urls
urlpatterns += [
    path("telegram/webhook/<int:connection_id>/", TelegramWebhookAPIView.as_view(), name="telegram-webhook"),
    path("whatsapp/webhook/<int:connection_id>/", WhatsAppWebhookAPIView.as_view(), name="whatsapp-webhook"),
    path("viber/webhook/<int:connection_id>/", ViberWebhookAPIView.as_view(), name="viber-webhook"),
    path("google-calendar/start/", google_calendar_start, name="gcal-start"),
    path("google-calendar/callback/", google_calendar_callback, name="gcal-callback"),
    path("google-calendar/disconnect/", google_calendar_disconnect, name="gcal-disconnect"),
]
