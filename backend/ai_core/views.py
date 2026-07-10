from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from ai_core.models import AlarmEvent, AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings
from ai_core.serializers import (
    AlarmEventSerializer,
    AlarmSettingsSerializer,
    GlobalAISettingsSerializer,
    KaleyaCommandLogSerializer,
    KaleyaCommandSerializer,
    VoiceSettingsSerializer,
)
from ai_core.services import handle_kaleya_command
from clients.utils import client_for_request


class GlobalAISettingsViewSet(viewsets.ModelViewSet):
    serializer_class = GlobalAISettingsSerializer
    permission_classes = (IsAdminRole,)

    def get_queryset(self):
        return GlobalAISettings.objects.all()


class VoiceSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = VoiceSettingsSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return VoiceSettings.objects.none()
        return VoiceSettings.objects.filter(business_client=client)

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class AlarmSettingsViewSet(viewsets.ModelViewSet):
    serializer_class = AlarmSettingsSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AlarmSettings.objects.none()
        return AlarmSettings.objects.filter(business_client=client)

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class KaleyaCommandLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = KaleyaCommandLogSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return KaleyaCommandLog.objects.none()
        return KaleyaCommandLog.objects.filter(business_client=client)


class AlarmEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Dashboard polls GET /api/ai/alarm-queue/ every ~30s for pending alarms.
    By default returns only undismissed alarms from the last 2 hours.
    POST /api/ai/alarm-queue/{id}/dismiss/  marks one as dismissed.
    POST /api/ai/alarm-queue/{id}/delivered/  marks delivered_at (optional).
    """

    serializer_class = AlarmEventSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AlarmEvent.objects.none()
        qs = AlarmEvent.objects.filter(business_client=client)
        if self.request.query_params.get("include_dismissed") != "1":
            # Pending only: exclude already-played (delivered) and stale alarms,
            # otherwise every page reload replays the whole history in a loop.
            qs = qs.filter(
                dismissed_at__isnull=True,
                delivered_at__isnull=True,
                created_at__gte=timezone.now() - timedelta(hours=2),
            )
        return qs

    @action(detail=True, methods=["post"])
    def dismiss(self, request, pk=None):
        alarm = self.get_object()
        if not alarm.dismissed_at:
            alarm.dismissed_at = timezone.now()
            alarm.save(update_fields=["dismissed_at"])
        return Response(self.get_serializer(alarm).data)

    @action(detail=True, methods=["post"])
    def delivered(self, request, pk=None):
        alarm = self.get_object()
        if not alarm.delivered_at:
            alarm.delivered_at = timezone.now()
            channels = list(alarm.channels or [])
            if "dashboard" not in channels:
                channels.append("dashboard")
            alarm.channels = channels
            alarm.save(update_fields=["delivered_at", "channels"])
        return Response(self.get_serializer(alarm).data)


class KaleyaCommandAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = KaleyaCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        output_text = handle_kaleya_command(
            client,
            serializer.validated_data["command"],
            serializer.validated_data.get("input_text", ""),
            serializer.validated_data.get("channel", "web"),
        )
        log = KaleyaCommandLog.objects.create(
            business_client=client,
            command=serializer.validated_data["command"],
            input_text=serializer.validated_data.get("input_text", ""),
            output_text=output_text,
            language=client.interface_language or client.language,
            channel=serializer.validated_data.get("channel", "web"),
            success=True,
        )
        return Response({"output_text": output_text, "log": KaleyaCommandLogSerializer(log).data})
