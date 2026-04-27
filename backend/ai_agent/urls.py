from django.urls import path
from rest_framework.routers import DefaultRouter

from ai_agent.views import AIIntentViewSet, AIToolRunViewSet, InboundTextAPIView


router = DefaultRouter()
router.register("intents", AIIntentViewSet, basename="ai-intent")
router.register("tool-runs", AIToolRunViewSet, basename="ai-tool-run")

urlpatterns = [
    path("inbound-text/", InboundTextAPIView.as_view(), name="ai-agent-inbound-text"),
] + router.urls
