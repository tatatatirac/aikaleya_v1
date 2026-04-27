from rest_framework.routers import DefaultRouter

from audit_log.views import AuditLogViewSet


router = DefaultRouter()
router.register("events", AuditLogViewSet, basename="audit-log")

urlpatterns = router.urls
