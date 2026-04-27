from django.conf import settings
from django.db import models

from clients.models import BusinessClient


class AuditLog(models.Model):
    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="audit_logs", null=True, blank=True)
    action = models.CharField(max_length=160)
    object_type = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=80, blank=True)
    channel = models.CharField(max_length=40, default="system")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("business_client", "created_at")),
            models.Index(fields=("action",)),
        ]

    def __str__(self):
        return f"{self.action} - {self.created_at:%Y-%m-%d %H:%M}"
