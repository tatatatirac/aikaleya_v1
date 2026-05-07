from rest_framework.routers import DefaultRouter
from django.urls import path

from billing.views import (
    CheckoutPublicDetailView,
    CheckoutSessionViewSet,
    LemonSqueezyWebhookView,
    PaymentWebhookEventViewSet,
    PayPalPublicConfigView,
    PayPalWebhookView,
    PlanViewSet,
    SubscriptionViewSet,
)


router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("checkout-sessions", CheckoutSessionViewSet, basename="checkout-session")
router.register("webhook-events", PaymentWebhookEventViewSet, basename="payment-webhook-event")

urlpatterns = [
    path("checkout-sessions/public/<uuid:public_id>/", CheckoutPublicDetailView.as_view(), name="checkout-public-detail"),
    path("payment/public-config/", PayPalPublicConfigView.as_view(), name="payment-public-config"),
    path("paypal/public-config/", PayPalPublicConfigView.as_view(), name="paypal-public-config"),
    path("paypal/webhook/", PayPalWebhookView.as_view(), name="paypal-webhook"),
    path("lemonsqueezy/webhook/", LemonSqueezyWebhookView.as_view(), name="lemonsqueezy-webhook"),
]

urlpatterns += router.urls
