from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_agent.models import AIIntent, AIToolRun
from ai_agent.providers import ProviderError, get_client_ai_config, get_client_voice_config, synthesize_elevenlabs_speech
from ai_agent.serializers import AIIntentSerializer, AIToolRunSerializer, InboundTextSerializer, TextToSpeechSerializer
from ai_agent.services import handle_inbound_text
from appointments.models import Customer
from billing.services import enforce_channel_allowed, enforce_elevenlabs_voice_allowed
from clients.utils import client_for_request
from communications.models import Conversation


class AIIntentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIIntentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AIIntent.objects.none()
        return AIIntent.objects.select_related("conversation", "customer").filter(business_client=client)


class AIToolRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AIToolRunSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return AIToolRun.objects.none()
        return AIToolRun.objects.select_related("intent").filter(business_client=client)


class InboundTextAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = InboundTextSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        enforce_channel_allowed(client, serializer.validated_data.get("channel", "web"))

        conversation = None
        customer = None
        if serializer.validated_data.get("conversation_id"):
            conversation = Conversation.objects.filter(
                id=serializer.validated_data["conversation_id"],
                business_client=client,
            ).first()
        if serializer.validated_data.get("customer_id"):
            customer = Customer.objects.filter(
                id=serializer.validated_data["customer_id"],
                business_client=client,
            ).first()

        result = handle_inbound_text(
            client,
            serializer.validated_data["text"],
            conversation=conversation,
            customer=customer,
            channel=serializer.validated_data.get("channel", "web"),
            payload={
                key: serializer.validated_data.get(key)
                for key in (
                    "customer_name",
                    "phone",
                    "email",
                    "appointment_id",
                    "customer_id",
                    "service_id",
                    "service_hint",
                    "staff_member_id",
                    "staff_hint",
                    "date",
                    "time",
                    "duration_minutes",
                    "title",
                )
                if key in serializer.validated_data
            },
            use_ai=serializer.validated_data.get("use_ai", True),
            include_voice=serializer.validated_data.get("include_voice", False),
        )
        return Response(result)


class TextToSpeechAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        serializer = TextToSpeechSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        enforce_elevenlabs_voice_allowed(client)

        try:
            return Response(synthesize_elevenlabs_speech(client, serializer.validated_data["text"]))
        except ProviderError as exc:
            return Response({"detail": str(exc)}, status=400)


class VoiceStatusAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        config = get_client_voice_config(client)
        api_key_set = bool(config.get("api_key"))
        voice_id_set = bool(config.get("voice_id"))
        package_allows_voice = False
        try:
            enforce_elevenlabs_voice_allowed(client)
            package_allows_voice = True
        except Exception:
            package_allows_voice = False
        return Response(
            {
                "provider": "elevenlabs",
                "connected": package_allows_voice and api_key_set and voice_id_set,
                "package_allows_voice": package_allows_voice,
                "api_key_set": api_key_set,
                "voice_id_set": voice_id_set,
                "model_id": config.get("model_id", ""),
            }
        )


class ProviderStatusAPIView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        ai_config = get_client_ai_config(client)
        voice_config = get_client_voice_config(client)
        package_allows_voice = False
        try:
            enforce_elevenlabs_voice_allowed(client)
            package_allows_voice = True
        except Exception:
            package_allows_voice = False
        return Response(
            {
                "ai": {
                    "provider": ai_config.get("provider", ""),
                    "model": ai_config.get("model", ""),
                    "connected": bool(ai_config.get("api_key")),
                },
                "voice": {
                    "provider": voice_config.get("provider", "elevenlabs"),
                    "model_id": voice_config.get("model_id", ""),
                    "connected": package_allows_voice and bool(voice_config.get("api_key")) and bool(voice_config.get("voice_id")),
                    "package_allows_voice": package_allows_voice,
                },
            }
        )
