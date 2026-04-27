from rest_framework import permissions, viewsets

from audit_log.models import AuditLog
from audit_log.serializers import AuditLogSerializer
from clients.utils import client_for_request


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AuditLog.objects.none()
        return AuditLog.objects.select_related("business_client", "actor").filter(business_client=client)
