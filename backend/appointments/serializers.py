from rest_framework import serializers

from appointments.models import Appointment, Customer


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

    class Meta:
        model = Appointment
        fields = (
            "id",
            "customer",
            "customer_id",
            "customer_data",
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

    def create(self, validated_data):
        business_client = self.context["business_client"]
        customer_id = validated_data.pop("customer_id", None)
        customer_data = validated_data.pop("customer_data", None)

        customer = None
        if customer_id:
            customer = Customer.objects.get(id=customer_id, business_client=business_client)
        elif customer_data:
            customer = Customer.objects.create(business_client=business_client, **customer_data)

        appointment = Appointment(business_client=business_client, customer=customer, **validated_data)
        appointment.full_clean()
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

        instance.full_clean()
        instance.save()
        return instance

