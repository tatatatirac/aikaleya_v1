from django.urls import path
from rest_framework.routers import DefaultRouter

from ai_core.views import (
    AlarmSettingsViewSet,
    GlobalAISettingsViewSet,
    KaleyaCommandAPIView,
    KaleyaCommandLogViewSet,
    VoiceSettingsViewSet,
)


router = DefaultRouter()
router.register("global-settings", GlobalAISettingsViewSet, basename="global-ai-settings")
router.register("voice-settings", VoiceSettingsViewSet, basename="voice-settings")
router.register("alarm-settings", AlarmSettingsViewSet, basename="alarm-settings")
router.register("command-logs", KaleyaCommandLogViewSet, basename="kaleya-command-log")

urlpatterns = [
    path("command/", KaleyaCommandAPIView.as_view(), name="kaleya-command"),
] + router.urls

