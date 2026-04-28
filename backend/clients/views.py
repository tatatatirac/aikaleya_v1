from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, user_role
from clients.models import BusinessClient, ClientApiSettings
from clients.serializers import BusinessClientSerializer, ClientApiSettingsSerializer
from clients.utils import client_for_request


class BusinessClientViewSet(viewsets.ModelViewSet):
    serializer_class = BusinessClientSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        role = user_role(self.request.user)
        if role == "admin":
            return BusinessClient.objects.select_related("owner", "api_settings").all()
        if role == "employee":
            client = client_for_request(self.request)
            if not client:
                return BusinessClient.objects.none()
            return BusinessClient.objects.select_related("owner", "api_settings").filter(id=client.id)
        return BusinessClient.objects.select_related("owner", "api_settings").filter(owner=self.request.user)

    def perform_create(self, serializer):
        owner = self.request.user
        if user_role(self.request.user) == "admin":
            owner = serializer.validated_data.get("owner", self.request.user)
        client = serializer.save(owner=owner)
        ClientApiSettings.objects.get_or_create(business_client=client)

    @action(detail=False, methods=["get", "patch"], url_path="current")
    def current(self, request):
        client = client_for_request(request)
        if client is None:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        if request.method == "PATCH":
            if user_role(request.user) == "employee":
                return Response(
                    {"detail": "Zaposleni ne moze da menja podesavanja firme."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            serializer = self.get_serializer(client, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(self.get_serializer(client).data)


class ClientApiSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = ClientApiSettingsSerializer
    permission_classes = (IsAdminRole,)

    def get_queryset(self):
        return ClientApiSettings.objects.select_related("business_client").all()
