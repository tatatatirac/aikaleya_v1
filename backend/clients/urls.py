from rest_framework.routers import DefaultRouter

from clients.views import BusinessClientViewSet, BusinessKnowledgeEntryViewSet, ClientApiSettingsViewSet


router = DefaultRouter()
router.register("business-clients", BusinessClientViewSet, basename="business-client")
router.register("api-settings", ClientApiSettingsViewSet, basename="client-api-settings")
router.register("knowledge", BusinessKnowledgeEntryViewSet, basename="business-knowledge")

urlpatterns = router.urls
