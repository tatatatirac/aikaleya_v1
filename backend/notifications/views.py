from rest_framework import permissions, viewsets

from clients.utils import client_for_request
from notifications.models import NotificationJob, NotificationRule
from notifications.serializers import NotificationJobSerializer, NotificationRuleSerializer


class NotificationRuleViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationRuleSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return NotificationRule.objects.none()
        return NotificationRule.objects.filter(business_client=client)

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class NotificationJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationJobSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return NotificationJob.objects.none()
        return NotificationJob.objects.select_related("appointment", "customer").filter(business_client=client)
