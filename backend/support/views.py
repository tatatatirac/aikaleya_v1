from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied, NotFound

from accounts.permissions import user_role
from clients.models import BusinessClient, get_active_client_for_user
from staff_services.models import StaffMember
from support.models import SupportTicket
from support.serializers import SupportTicketSerializer


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_employee_client(self):
        profile = getattr(self.request.user, "profile", None)
        if getattr(profile, "business_client", None):
            return profile.business_client
        staff_member = StaffMember.objects.select_related("business_client").filter(user=self.request.user).first()
        return staff_member.business_client if staff_member else None

    def get_client(self):
        role = user_role(self.request.user)
        if role == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                client = BusinessClient.objects.filter(id=client_id).first()
                if not client:
                    raise NotFound("Klijent nije pronadjen.")
                return client
            return None
        if role == "employee":
            return self.get_employee_client()
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        role = user_role(self.request.user)
        if role == "admin" and not self.request.query_params.get("client_id"):
            return SupportTicket.objects.select_related("business_client").all()
        client = self.get_client()
        if not client:
            return SupportTicket.objects.none()
        queryset = SupportTicket.objects.filter(business_client=client)
        if role == "employee":
            queryset = queryset.filter(metadata__created_by_user_id=self.request.user.id)
        return queryset

    def perform_create(self, serializer):
        client = self.get_client()
        if not client:
            raise PermissionDenied("Samo vlasnik, radnik ili admin moze da otvori support zahtev.")

        role = user_role(self.request.user)
        profile = getattr(self.request.user, "profile", None)
        staff_member = StaffMember.objects.filter(user=self.request.user, business_client=client).first()
        requester_name = (
            getattr(staff_member, "full_name", "")
            or self.request.user.get_full_name()
            or self.request.user.email
            or self.request.user.username
        )
        requester_phone = getattr(staff_member, "phone", "") or getattr(profile, "phone", "")
        metadata = dict(serializer.validated_data.get("metadata") or {})
        metadata.update(
            {
                "created_by_user_id": self.request.user.id,
                "requester_role": role,
                "requester_name": requester_name,
                "requester_email": self.request.user.email or self.request.user.username,
                "requester_phone": requester_phone,
                "source": metadata.get("source") or "app_support",
            }
        )
        serializer.save(business_client=client, metadata=metadata)
