from rest_framework import permissions, viewsets

from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user
from integrations.models import IntegrationConnection
from integrations.serializers import IntegrationConnectionSerializer


class IntegrationConnectionViewSet(viewsets.ModelViewSet):
    serializer_class = IntegrationConnectionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_client(self):
        if user_role(self.request.user) == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                return BusinessClient.objects.get(id=client_id)
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return IntegrationConnection.objects.none()
        return IntegrationConnection.objects.filter(business_client=client)

    def perform_create(self, serializer):
        serializer.save(business_client=self.get_client())

