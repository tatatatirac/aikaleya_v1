from django.urls import path
from rest_framework.routers import DefaultRouter

from integrations.views import IntegrationConnectionViewSet, TelegramWebhookAPIView


router = DefaultRouter()
router.register("connections", IntegrationConnectionViewSet, basename="integration-connection")

urlpatterns = router.urls
urlpatterns += [
    path("telegram/webhook/<int:connection_id>/", TelegramWebhookAPIView.as_view(), name="telegram-webhook"),
]
