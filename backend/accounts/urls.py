from django.urls import path

from accounts.views import LoginAPIView, LogoutAPIView, MeAPIView


urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="login"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
]

