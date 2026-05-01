from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user
from integrations.models import IntegrationConnection
from integrations.serializers import IntegrationConnectionSerializer
from integrations.services import integration_rows_for_client, queue_test_message


class IntegrationConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationConnectionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_client(self):
        if user_role(self.request.user) == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                return BusinessClient.objects.get(id=client_id)
            return BusinessClient.objects.first()
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return IntegrationConnection.objects.none()
        return IntegrationConnection.objects.filter(business_client=client)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = self.get_client()
        return context

    def perform_create(self, serializer):
        serializer.save(business_client=self.get_client())

    @action(detail=False, methods=["get"], url_path="status")
    def connection_status(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"business_client": client.id, "integrations": integration_rows_for_client(client)})

    @action(detail=False, methods=["post"], url_path="test-message")
    def test_message(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=status.HTTP_404_NOT_FOUND)
        if getattr(client, "is_demo", False):
            return Response(
                {"detail": "Demo nalog ne salje stvarne test poruke niti koristi spoljne integracije."},
                status=status.HTTP_403_FORBIDDEN,
            )

        provider = request.data.get("provider", "")
        to_value = request.data.get("to", "")
        body = request.data.get("body", "")
        if not to_value:
            return Response({"to": "Unesite broj telefona, email ili ID primaoca."}, status=status.HTTP_400_BAD_REQUEST)
        if not body:
            return Response({"body": "Unesite tekst test poruke."}, status=status.HTTP_400_BAD_REQUEST)

        conversation, message = queue_test_message(client, provider, to_value, body)
        return Response(
            {
                "status": "queued",
                "delivery_note": "Poruka je upisana u red za slanje. Stvarno slanje se ukljucuje kada se poveze provider nalog.",
                "conversation_id": conversation.id,
                "message_id": message.id,
                "provider": provider,
            },
            status=status.HTTP_202_ACCEPTED,
        )
