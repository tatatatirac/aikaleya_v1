from django.urls import path
from rest_framework.routers import DefaultRouter

from communications.sms_views import sms_incoming
from communications.views import CallSessionViewSet, ConversationViewSet, MessageViewSet
from communications.voice_views import voice_gather, voice_incoming, voice_status
from communications.whatsapp_views import whatsapp_incoming


router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("messages", MessageViewSet, basename="message")
router.register("calls", CallSessionViewSet, basename="call-session")

urlpatterns = router.urls
urlpatterns += [
    path("voice/incoming/", voice_incoming, name="voice-incoming"),
    path("voice/gather/<int:session_id>/", voice_gather, name="voice-gather"),
    path("voice/status/<int:session_id>/", voice_status, name="voice-status"),
    path("sms/incoming/", sms_incoming, name="sms-incoming"),
    path("whatsapp/incoming/", whatsapp_incoming, name="whatsapp-incoming"),
]
