from rest_framework import serializers

from clients.utils import client_for_request
from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours


class StaffMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffMember
        fields = (
            "id",
            "full_name",
            "role_title",
            "phone",
            "email",
            "color",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "category",
            "description",
            "duration_minutes",
            "price",
            "currency",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class StaffServiceSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.CharField(source="staff_member.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = StaffService
        fields = ("id", "staff_member", "staff_member_name", "service", "service_name", "is_active", "created_at")
        read_only_fields = ("id", "staff_member_name", "service_name", "created_at")

    def validate(self, attrs):
        request = self.context.get("request")
        client = client_for_request(request) if request else None
        staff_member = attrs.get("staff_member", getattr(self.instance, "staff_member", None))
        service = attrs.get("service", getattr(self.instance, "service", None))

        if client and staff_member and staff_member.business_client_id != client.id:
            raise serializers.ValidationError({"staff_member": "Zaposleni ne pripada ovom klijentu."})
        if client and service and service.business_client_id != client.id:
            raise serializers.ValidationError({"service": "Usluga ne pripada ovom klijentu."})

        if staff_member and service:
            duplicate = StaffService.objects.filter(staff_member=staff_member, service=service)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError("Ovaj zaposleni vec ima povezanu ovu uslugu.")

        return attrs


class WorkingHoursSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingHours
        fields = ("id", "staff_member", "weekday", "start_time", "end_time", "is_closed")
        read_only_fields = ("id",)


class BlockedTimeSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.CharField(source="staff_member.full_name", read_only=True)

    class Meta:
        model = BlockedTime
        fields = ("id", "staff_member", "staff_member_name", "start_at", "end_at", "reason", "source", "created_at")
        read_only_fields = ("id", "staff_member_name", "created_at")

    def validate(self, attrs):
        request = self.context.get("request")
        client = client_for_request(request) if request else None
        staff_member = attrs.get("staff_member", getattr(self.instance, "staff_member", None))
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))

        if client and staff_member and staff_member.business_client_id != client.id:
            raise serializers.ValidationError({"staff_member": "Zaposleni ne pripada ovom klijentu."})
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError({"end_at": "Kraj blokade mora biti posle pocetka."})

        return attrs
