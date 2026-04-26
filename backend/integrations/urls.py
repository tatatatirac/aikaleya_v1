from rest_framework.routers import DefaultRouter

from integrations.views import IntegrationConnectionViewSet


router = DefaultRouter()
router.register("connections", IntegrationConnectionViewSet, basename="integration-connection")

urlpatterns = router.urls

