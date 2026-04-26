from rest_framework.routers import DefaultRouter

from clients.views import BusinessClientViewSet, ClientApiSettingsViewSet


router = DefaultRouter()
router.register("business-clients", BusinessClientViewSet, basename="business-client")
router.register("api-settings", ClientApiSettingsViewSet, basename="client-api-settings")

urlpatterns = router.urls

