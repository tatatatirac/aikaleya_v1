from django.utils import timezone
from rest_framework import permissions, viewsets

from clients.utils import client_for_request
from communications.models import CallSession, Conversation, Message
from communications.serializers import CallSessionSerializer, ConversationSerializer, MessageSerializer


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Conversation.objects.none()
        return Conversation.objects.select_related("customer").prefetch_related("messages").filter(business_client=client)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = client_for_request(self.request)
        return context

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Message.objects.none()
        return Message.objects.select_related("conversation").filter(conversation__business_client=client)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = client_for_request(self.request)
        return context

    def perform_create(self, serializer):
        message = serializer.save()
        Conversation.objects.filter(id=message.conversation_id).update(last_message_at=timezone.now())


class CallSessionViewSet(viewsets.ModelViewSet):
    serializer_class = CallSessionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return CallSession.objects.none()
        return CallSession.objects.select_related("conversation", "customer").filter(business_client=client)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = client_for_request(self.request)
        return context

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))
