from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, user_role
from ai_core.models import AlarmSettings, GlobalAISettings, KaleyaCommandLog, VoiceSettings
from ai_core.serializers import (
    AlarmSettingsSerializer,
    GlobalAISettingsSerializer,
    KaleyaCommandLogSerializer,
    KaleyaCommandSerializer,
    VoiceSettingsSerializer,
)
from ai_core.services import handle_kaleya_command
from clients.models import BusinessClient, get_active_client_for_user


def client_for_request(request):
    if user_role(request.user) == "admin":
        client_id = request.query_params.get("client_id") or request.data.get("business_client")
        if client_id:
            return BusinessClient.objects.get(id=client_id)
    return get_active_client_for_user(request.user)


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

