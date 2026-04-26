from django.urls import path

from appointments.consumers import ClientCalendarConsumer

websocket_urlpatterns = [
    path("ws/clients/<int:client_id>/calendar/", ClientCalendarConsumer.as_asgi()),
]
