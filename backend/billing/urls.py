from rest_framework.routers import DefaultRouter
from django.urls import path

from billing.views import CheckoutSessionViewSet, PayPalWebhookView, PlanViewSet, SubscriptionViewSet


router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("checkout-sessions", CheckoutSessionViewSet, basename="checkout-session")

urlpatterns = [
    path("paypal/webhook/", PayPalWebhookView.as_view(), name="paypal-webhook"),
]

urlpatterns += router.urls
