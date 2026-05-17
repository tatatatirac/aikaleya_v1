from django.urls import path

from accounts.views import (
    GdprCancelDeleteAPIView,
    GdprDeleteAccountAPIView,
    GdprExportAPIView,
    LoginAPIView,
    LogoutAPIView,
    MeAPIView,
    OnboardingCompleteAPIView,
    RegisterClientAPIView,
)


urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("register-client/", RegisterClientAPIView.as_view(), name="register-client"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("onboarding/complete/", OnboardingCompleteAPIView.as_view(), name="onboarding-complete"),
    path("gdpr/export/", GdprExportAPIView.as_view(), name="gdpr-export"),
    path("gdpr/delete-account/", GdprDeleteAccountAPIView.as_view(), name="gdpr-delete-account"),
    path("gdpr/cancel-delete/", GdprCancelDeleteAPIView.as_view(), name="gdpr-cancel-delete"),
]
