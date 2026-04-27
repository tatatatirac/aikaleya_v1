from rest_framework.routers import DefaultRouter

from staff_services.views import (
    BlockedTimeViewSet,
    ServiceViewSet,
    StaffMemberViewSet,
    StaffServiceViewSet,
    WorkingHoursViewSet,
)


router = DefaultRouter()
router.register("staff", StaffMemberViewSet, basename="staff")
router.register("services", ServiceViewSet, basename="service")
router.register("staff-services", StaffServiceViewSet, basename="staff-service")
router.register("working-hours", WorkingHoursViewSet, basename="working-hours")
router.register("blocked-times", BlockedTimeViewSet, basename="blocked-time")

urlpatterns = router.urls
