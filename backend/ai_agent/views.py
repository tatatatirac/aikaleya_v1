from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_agent.models import AIIntent, AIToolRun
from ai_agent.providers import ProviderError, synthesize_elevenlabs_speech
from ai_agent.serializers import AIIntentSerializer, AIToolRunSerializer, InboundTextSerializer, TextToSpeechSerializer
from ai_agent.services import handle_inbound_text
from appointments.models import Customer
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

        try:
            return Response(synthesize_elevenlabs_speech(client, serializer.validated_data["text"]))
        except ProviderError as exc:
            return Response({"detail": str(exc)}, status=400)
