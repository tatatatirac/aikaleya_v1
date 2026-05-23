from datetime import datetime

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from accounts.permissions import user_role
from appointments.models import Appointment, Customer
from appointments.serializers import AppointmentSerializer, CustomerSerializer
from appointments.services import availability_for_date, client_timezone, today_availability_summary
from clients.utils import client_for_request


def staff_member_for_employee(user):
    if user_role(user) != "employee":
        return None
    return getattr(user, "staff_member_profile", None)


class ClientAppointmentPermission(permissions.IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        role = user_role(request.user)
        if role in {"admin", "client"}:
            return True
        if role == "employee" and view.__class__.__name__ == "AppointmentViewSet":
            return getattr(view, "action", "") in {"create", "cancel"}
        return False


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = (ClientAppointmentPermission,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Customer.objects.none()
        queryset = Customer.objects.filter(business_client=client)
        staff_member = staff_member_for_employee(self.request.user)
        if staff_member:
            customer_ids = Appointment.objects.filter(
                business_client=client,
                staff_member=staff_member,
                customer__isnull=False,
            ).values("customer_id")
            queryset = queryset.filter(id__in=customer_ids)
        return queryset

    def perform_create(self, serializer):
        serializer.save(business_client=client_for_request(self.request))


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = (ClientAppointmentPermission,)

    def get_queryset(self):
        client = client_for_request(self.request)
        if not client:
            return Appointment.objects.none()

        queryset = Appointment.objects.select_related("customer", "staff_member", "service").filter(business_client=client)
        staff_member = staff_member_for_employee(self.request.user)
        if user_role(self.request.user) == "employee":
            if not staff_member:
                return Appointment.objects.none()
            queryset = queryset.filter(staff_member=staff_member)

        target_date = self.request.query_params.get("date")
        status_filter = self.request.query_params.get("status")

        if target_date:
            queryset = queryset.filter(date=target_date)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Hide soft-deleted appointments from calendar view by default
        # (dossier endpoint queries directly without this filter)
        queryset = queryset.filter(hidden_in_calendar=False)

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
        staff_member = staff_member_for_employee(request.user)
        if staff_member:
            staff_member_id = staff_member.id
        target_date = (
            datetime.strptime(date_value, "%Y-%m-%d").date()
            if date_value
            else timezone.localtime(timezone.now(), client_timezone(client)).date()
        )
        duration = int(duration_value) if duration_value else None

        return Response(availability_for_date(client, target_date, duration, staff_member_id=staff_member_id))

    @action(detail=False, methods=["get"], url_path="today-summary")
    def today_summary(self, request):
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Klijent nije pronadjen."}, status=404)
        staff_member_id = request.query_params.get("staff_member")
        staff_member = staff_member_for_employee(request.user)
        if staff_member:
            staff_member_id = staff_member.id
        return Response(today_availability_summary(client, staff_member_id=staff_member_id))

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        client = client_for_request(request)
        query = request.query_params.get("q", "").strip()
        queryset = Appointment.objects.select_related("customer").filter(business_client=client)
        staff_member = staff_member_for_employee(request.user)
        if staff_member:
            queryset = queryset.filter(staff_member=staff_member)

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

    @action(detail=True, methods=["post"], url_path="hide")
    def hide(self, request, pk=None):
        """Soft-delete: hide appointment from calendar view without erasing history."""
        appointment = Appointment.objects.get(
            pk=pk, business_client=client_for_request(request)
        )
        appointment.hidden_in_calendar = True
        appointment.save(update_fields=["hidden_in_calendar", "updated_at"])
        return Response({"status": "hidden", "id": appointment.id}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="dossier")
    def dossier(self, request):
        """Return client history statistics by phone number or name for the dossier panel."""
        client = client_for_request(request)
        if not client:
            return Response({"detail": "Client not found."}, status=404)

        phone = request.query_params.get("phone", "").strip()
        name = request.query_params.get("name", "").strip()

        if not phone and not name:
            return Response({"detail": "Provide phone or name."}, status=400)

        # Query ALL appointments for this business client — including hidden ones
        qs = Appointment.objects.select_related("customer", "service").filter(
            business_client=client
        ).exclude(status=Appointment.STATUS_BLOCKED)

        if phone:
            qs = qs.filter(customer__phone__icontains=phone)
        elif name:
            qs = qs.filter(
                Q(customer__first_name__icontains=name)
                | Q(customer__last_name__icontains=name)
                | Q(title__icontains=name)
            )

        total = qs.count()
        cancelled = qs.filter(status=Appointment.STATUS_CANCELLED).count()
        services_used = list(
            qs.filter(service__isnull=False)
            .values_list("service__name", flat=True)
            .distinct()[:15]
        )
        hidden_count = qs.filter(hidden_in_calendar=True).count()

        # Customer info
        first_appt = qs.order_by("date", "start_time").first()
        customer_name = ""
        customer_phone = ""
        if first_appt and first_appt.customer:
            customer_name = first_appt.customer.full_name
            customer_phone = first_appt.customer.phone

        return Response({
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "total": total,
            "cancelled": cancelled,
            "hidden_in_calendar": hidden_count,
            "services": services_used,
        })
