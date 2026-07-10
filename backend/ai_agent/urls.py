from django.urls import path
from rest_framework.routers import DefaultRouter

from ai_agent.views import (
    AIIntentViewSet,
    AIToolRunViewSet,
    CustomerMemoryViewSet,
    InboundTextAPIView,
    ProviderStatusAPIView,
    PublicBookingChatAPIView,
    PublicBrowserChatAPIView,
    PublicIntroSpeechAPIView,
    TextToSpeechAPIView,
    VoiceStatusAPIView,
)


router = DefaultRouter()
router.register("intents", AIIntentViewSet, basename="ai-intent")
router.register("tool-runs", AIToolRunViewSet, basename="ai-tool-run")
router.register("customer-memories", CustomerMemoryViewSet, basename="customer-memory")

urlpatterns = [
    path("inbound-text/", InboundTextAPIView.as_view(), name="ai-agent-inbound-text"),
    path("public-intro-tts/", PublicIntroSpeechAPIView.as_view(), name="ai-agent-public-intro-tts"),
    path("tts/", TextToSpeechAPIView.as_view(), name="ai-agent-tts"),
    path("voice-status/", VoiceStatusAPIView.as_view(), name="ai-agent-voice-status"),
    path("provider-status/", ProviderStatusAPIView.as_view(), name="ai-agent-provider-status"),
    path("public-browser-chat/", PublicBrowserChatAPIView.as_view(), name="ai-agent-public-browser-chat"),
    path("public-booking/<int:client_id>/", PublicBookingChatAPIView.as_view(), name="ai-agent-public-booking"),
] + router.urls
