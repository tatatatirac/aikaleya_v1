from rest_framework.routers import DefaultRouter

from communications.views import CallSessionViewSet, ConversationViewSet, MessageViewSet


router = DefaultRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("messages", MessageViewSet, basename="message")
router.register("calls", CallSessionViewSet, basename="call-session")

urlpatterns = router.urls
