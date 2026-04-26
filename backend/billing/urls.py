from rest_framework.routers import DefaultRouter

from billing.views import PlanViewSet, SubscriptionViewSet


router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = router.urls

