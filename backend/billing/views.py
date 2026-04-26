from rest_framework import permissions, viewsets

from accounts.permissions import IsAdminRole, user_role
from billing.models import Plan, Subscription
from billing.serializers import PlanSerializer, SubscriptionSerializer
from clients.models import BusinessClient, get_active_client_for_user


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return [IsAdminRole()]

    def get_queryset(self):
        return Plan.objects.filter(active=True)


class SubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_client(self):
        if user_role(self.request.user) == "admin":
            client_id = self.request.query_params.get("client_id") or self.request.data.get("business_client")
            if client_id:
                return BusinessClient.objects.get(id=client_id)
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return Subscription.objects.none()
        return Subscription.objects.select_related("plan").filter(business_client=client)

    def perform_create(self, serializer):
        plan = Plan.objects.get(id=serializer.validated_data.pop("plan_id"))
        serializer.save(business_client=self.get_client(), plan=plan)

