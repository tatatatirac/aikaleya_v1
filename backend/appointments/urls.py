from rest_framework.routers import DefaultRouter

from appointments.views import AppointmentViewSet, CustomerViewSet


router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls

