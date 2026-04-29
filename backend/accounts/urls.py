from django.urls import path

from accounts.views import LoginAPIView, LogoutAPIView, MeAPIView, RegisterClientAPIView


urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("register-client/", RegisterClientAPIView.as_view(), name="register-client"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
]
