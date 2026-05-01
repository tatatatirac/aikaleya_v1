from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.permissions import user_role
from appointments.models import Appointment, Customer
from staff_services.models import StaffService


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "email",
            "preferred_channel",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "full_name", "created_at", "updated_at")


class AppointmentSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    customer_data = CustomerSerializer(write_only=True, required=False)
    end_time = serializers.TimeField(read_only=True)
    staff_member_name = serializers.CharField(source="staff_member.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "customer",
            "customer_id",
            "customer_data",
            "staff_member",
            "staff_member_name",
            "service",
            "service_name",
            "title",
            "status",
            "date",
            "start_time",
            "end_time",
            "duration_minutes",
            "channel",
            "source",
            "notes",
            "cancelled_reason",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "end_time", "created_at", "updated_at")

    def validate_customer_id(self, value):
        business_client = self.context["business_client"]
        if value is None:
            return value
        if not Customer.objects.filter(id=value, business_client=business_client).exists():
            raise serializers.ValidationError("Kupac ne pripada ovom klijentu.")
        return value

    def validate(self, attrs):
        business_client = self.context["business_client"]
        request = self.context.get("request")
        staff_member = attrs.get("staff_member", getattr(self.instance, "staff_member", None))
        service = attrs.get("service", getattr(self.instance, "service", None))

        if request and user_role(request.user) == "employee":
            employee_staff = getattr(request.user, "staff_member_profile", None)
            if not employee_staff:
                raise serializers.ValidationError({"staff_member": "Zaposleni nema povezan staff profil."})
            if staff_member and staff_member.id != employee_staff.id:
                raise serializers.ValidationError({"staff_member": "Zaposleni moze da zakazuje samo svoje termine."})
            attrs["staff_member"] = employee_staff
            staff_member = employee_staff

        if staff_member and staff_member.business_client_id != business_client.id:
            raise serializers.ValidationError({"staff_member": "Zaposleni ne pripada ovom klijentu."})
        if service and service.business_client_id != business_client.id:
            raise serializers.ValidationError({"service": "Usluga ne pripada ovom klijentu."})
        if staff_member and service:
            allowed = StaffService.objects.filter(staff_member=staff_member, service=service, is_active=True).exists()
            if not allowed:
                raise serializers.ValidationError({"service": "Ovaj zaposleni nema ukljucenu izabranu uslugu."})
        return attrs

    def create(self, validated_data):
        business_client = self.context["business_client"]
        customer_id = validated_data.pop("customer_id", None)
        customer_data = validated_data.pop("customer_data", None)
        service = validated_data.get("service")
        if service and "duration_minutes" not in validated_data:
            validated_data["duration_minutes"] = service.duration_minutes

        customer = None
        if customer_id:
            customer = Customer.objects.get(id=customer_id, business_client=business_client)
        elif customer_data:
            customer = Customer.objects.create(business_client=business_client, **customer_data)

        appointment = Appointment(business_client=business_client, customer=customer, **validated_data)
        try:
            appointment.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        appointment.save()
        return appointment

    def update(self, instance, validated_data):
        customer_id = validated_data.pop("customer_id", None)
        customer_data = validated_data.pop("customer_data", None)

        if customer_id is not None:
            business_client = self.context["business_client"]
            instance.customer = Customer.objects.get(id=customer_id, business_client=business_client)
        elif customer_data:
            if instance.customer:
                for key, value in customer_data.items():
                    setattr(instance.customer, key, value)
                instance.customer.save()
            else:
                instance.customer = Customer.objects.create(
                    business_client=self.context["business_client"],
                    **customer_data,
                )

        for key, value in validated_data.items():
            setattr(instance, key, value)

        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()
        return instance
