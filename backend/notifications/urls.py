from rest_framework.routers import DefaultRouter

from notifications.views import NotificationJobViewSet, NotificationRuleViewSet


router = DefaultRouter()
router.register("rules", NotificationRuleViewSet, basename="notification-rule")
router.register("jobs", NotificationJobViewSet, basename="notification-job")

urlpatterns = router.urls
