from rest_framework import permissions, viewsets

from clients.utils import client_for_request
from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours
from staff_services.serializers import (
    BlockedTimeSerializer,
    ServiceSerializer,
    StaffMemberSerializer,
    StaffServiceSerializer,
    WorkingHoursSerializer,
)


class BusinessScopedMixin:
    permission_classes = (permissions.IsAuthenticated,)

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


class ServiceViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = ServiceSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return Service.objects.none()
        return Service.objects.filter(business_client=client)


class StaffServiceViewSet(viewsets.ModelViewSet):
    serializer_class = StaffServiceSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return StaffService.objects.none()
        return StaffService.objects.select_related("staff_member", "service").filter(
            staff_member__business_client=client,
            service__business_client=client,
        )


class WorkingHoursViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = WorkingHoursSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return WorkingHours.objects.none()
        return WorkingHours.objects.select_related("staff_member").filter(business_client=client)


class BlockedTimeViewSet(BusinessScopedMixin, viewsets.ModelViewSet):
    serializer_class = BlockedTimeSerializer

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return BlockedTime.objects.none()
        return BlockedTime.objects.select_related("staff_member").filter(business_client=client)
