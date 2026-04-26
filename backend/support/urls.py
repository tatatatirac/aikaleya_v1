from rest_framework.routers import DefaultRouter

from support.views import SupportTicketViewSet


router = DefaultRouter()
router.register("tickets", SupportTicketViewSet, basename="support-ticket")

urlpatterns = router.urls

