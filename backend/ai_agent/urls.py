from django.urls import path
from rest_framework.routers import DefaultRouter

from ai_agent.views import AIIntentViewSet, AIToolRunViewSet, InboundTextAPIView, TextToSpeechAPIView, VoiceStatusAPIView


router = DefaultRouter()
router.register("intents", AIIntentViewSet, basename="ai-intent")
router.register("tool-runs", AIToolRunViewSet, basename="ai-tool-run")

urlpatterns = [
    path("inbound-text/", InboundTextAPIView.as_view(), name="ai-agent-inbound-text"),
    path("tts/", TextToSpeechAPIView.as_view(), name="ai-agent-tts"),
    path("voice-status/", VoiceStatusAPIView.as_view(), name="ai-agent-voice-status"),
] + router.urls
