from datetime import date as date_cls
from datetime import datetime

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from appointments.models import Appointment, Customer
from appointments.serializers import AppointmentSerializer, CustomerSerializer
from appointments.services import availability_for_date, today_availability_summary
from clients.utils import client_for_request


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Customer.objects.none()
        return Customer.objects.filter(business_client=client)

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Appointment.objects.none()

        queryset = Appointment.objects.select_related("customer", "staff_member", "service").filter(business_client=client)
        target_date = self.request.query_params.get("date")
        status_filter = self.request.query_params.get("status")

        if target_date:
            queryset = queryset.filter(date=target_date)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["business_client"] = client_for_request(self.request)
        return context

    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)

        date_value = request.query_params.get("date")
        duration_value = request.query_params.get("duration_minutes")
        staff_member_id = request.query_params.get("staff_member")
        target_date = datetime.strptime(date_value, "%Y-%m-%d").date() if date_value else date_cls.today()
        duration = int(duration_value) if duration_value else None

        return Response(availability_for_date(client, target_date, duration, staff_member_id=staff_member_id))

    @action(detail=False, methods=["get"], url_path="today-summary")
    def today_summary(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        staff_member_id = request.query_params.get("staff_member")
        return Response(today_availability_summary(client, staff_member_id=staff_member_id))

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        client = client_for_request(request)
        query = request.query_params.get("q", "").strip()
        queryset = Appointment.objects.select_related("customer").filter(business_client=client)

        if query:
            queryset = queryset.filter(
                Q(customer__first_name__icontains=query)
                | Q(customer__last_name__icontains=query)
                | Q(customer__phone__icontains=query)
                | Q(title__icontains=query)
            )

        serializer = self.get_serializer(queryset.order_by("-date", "-start_time")[:30], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        appointment.status = Appointment.STATUS_CANCELLED
        appointment.cancelled_reason = request.data.get("reason", "")
        appointment.save(update_fields=["status", "cancelled_reason", "updated_at"])
        return Response(self.get_serializer(appointment).data, status=status.HTTP_200_OK)
