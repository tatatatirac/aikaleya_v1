from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, user_role
from billing.models import Plan, Subscription
from billing.serializers import PlanSerializer, SubscriptionSerializer
from billing.services import entitlements_for_client, plan_for_client
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
            return BusinessClient.objects.first()
        return get_active_client_for_user(self.request.user)

    def get_queryset(self):
        client = self.get_client()
        if not client:
            return Subscription.objects.none()
        return Subscription.objects.select_related("plan").filter(business_client=client)

    def perform_create(self, serializer):
        plan = Plan.objects.get(id=serializer.validated_data.pop("plan_id"))
        serializer.save(business_client=self.get_client(), plan=plan)

    @action(detail=False, methods=["get"], url_path="entitlements")
    def entitlements(self, request):
        client = self.get_client()
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        plan = plan_for_client(client)
        return Response(
            {
                "package": client.package,
                "plan": {
                    "code": plan.code if plan else client.package,
                    "name": plan.name if plan else client.get_package_display(),
                },
                "entitlements": entitlements_for_client(client),
            }
        )
