from rest_framework import permissions, viewsets
from django.db.models import Q

from accounts.permissions import user_role
from billing.services import enforce_staff_limit
from clients.utils import client_for_request
from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours
from staff_services.serializers import (
    BlockedTimeSerializer,
    ServiceSerializer,
    StaffMemberSerializer,
    StaffServiceSerializer,
    WorkingHoursSerializer,
)


def staff_member_for_employee(user):
    if user_role(user) != "employee":
        return None
    return getattr(user, "staff_member_profile", None)


class ClientConfigurationPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return user_role(request.user) in {"admin", "client"}


class BusinessScopedMixin:
    permission_classes = (ClientConfigurationPermission,)

    def get_client(self):
        return client_for_request(self.request)

    def perform_create(self, serializer):
        serializer.save(business_client=self.get_client())


class StaffMemberViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = StaffMemberSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return StaffMember.objects.none()
        return StaffMember.objects.filter(business_client=client)

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_active", True):
            enforce_staff_limit(self.get_client())
        serializer.save(business_client=self.get_client())


class ServiceViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return Service.objects.none()
        return Service.objects.filter(business_client=client)


class StaffServiceViewSet(viewsets.ModelViewSet):
    serializer_class = StaffServiceSerializer
    permission_classes = (ClientConfigurationPermission,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return StaffService.objects.none()
        return StaffService.objects.select_related("staff_member", "service").filter(
            staff_member__business_client=client,
            service__business_client=client,
        ).order_by("staff_member__full_name", "service__name")


class WorkingHoursViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = WorkingHoursSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return WorkingHours.objects.none()
        queryset = WorkingHours.objects.select_related("staff_member").filter(business_client=client)
        staff_member = staff_member_for_employee(self.request.user)
        if staff_member:
            queryset = queryset.filter(Q(staff_member=staff_member) | Q(staff_member__isnull=True))
        return queryset


class BlockedTimeViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = BlockedTimeSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return BlockedTime.objects.none()
        queryset = BlockedTime.objects.select_related("staff_member").filter(business_client=client)
        staff_member = staff_member_for_employee(self.request.user)
        if staff_member:
            queryset = queryset.filter(Q(staff_member=staff_member) | Q(staff_member__isnull=True))
        return queryset
