from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, NotFound

from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user
from support.models import SupportTicket
from support.serializers import SupportTicketSerializer


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_client(self):
        if user_role(self.request.user) == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                client = BusinessClient.objects.filter(id=client_id).first()
                if not client:
                    raise NotFound("Klijent nije pronadjen.")
                return client
            return None
        if user_role(self.request.user) == "employee":
            return None
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        if user_role(self.request.user) == "admin" and not self.request.query_params.get("client_id"):
            return SupportTicket.objects.select_related("business_client").all()
        client = self.get_client()
        if not client:
            return SupportTicket.objects.none()
        return SupportTicket.objects.filter(business_client=client)

    def perform_create(self, serializer):
        client = self.get_client()
        if not client:
            raise PermissionDenied("Samo vlasnik ili admin moze da otvori support zahtev.")
        serializer.save(business_client=client)
