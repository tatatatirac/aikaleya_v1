from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction

from accounts.models import Profile
from billing.services import enforce_staff_limit
from clients.utils import client_for_request
from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours


class StaffMemberSerializer(serializers.ModelSerializer):
    login_username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    login_password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = StaffMember
        fields = (
            "id",
            "user_username",
            "login_username",
            "login_password",
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

    def validate(self, attrs):
        login_username = attrs.get("login_username", "").strip()
        login_password = attrs.get("login_password", "")
        if (login_username and not login_password and not getattr(self.instance, "user_id", None)) or (login_password and not login_username and not getattr(self.instance, "user_id", None)):
            raise serializers.ValidationError({"login_username": "Za prvi login zaposlenog unesite korisnicko ime i lozinku."})
        if self.instance and not self.instance.is_active and attrs.get("is_active") is True:
            enforce_staff_limit(self.instance.business_client)
        return attrs

    def _sync_employee_user(self, staff_member, login_username="", login_password=""):
        login_username = (login_username or "").strip().lower()
        login_password = login_password or ""
        if not login_username and not login_password:
            return staff_member

        client = staff_member.business_client
        user = staff_member.user
        if login_username:
            existing = User.objects.filter(username__iexact=login_username).first()
            if existing and existing != user:
                raise serializers.ValidationError({"login_username": "Ovo korisnicko ime je vec zauzeto."})
            if user is None:
                user = User(username=login_username, email=staff_member.email if "@" in staff_member.email else "")
            user.username = login_username

        if staff_member.email and "@" in staff_member.email:
            user.email = staff_member.email
        user.first_name = staff_member.full_name.split(" ", 1)[0]
        user.last_name = staff_member.full_name.split(" ", 1)[1] if " " in staff_member.full_name else ""
        user.is_active = staff_member.is_active
        if login_password:
            user.set_password(login_password)
        user.save()

        profile, _created = Profile.objects.get_or_create(user=user)
        profile.role = Profile.ROLE_EMPLOYEE
        profile.business_client = client
        profile.phone = staff_member.phone
        profile.save(update_fields=["role", "business_client", "phone", "updated_at"])

        if staff_member.user_id != user.id:
            staff_member.user = user
            staff_member.save(update_fields=["user", "updated_at"])
        return staff_member

    @transaction.atomic
    def create(self, validated_data):
        login_username = validated_data.pop("login_username", "")
        login_password = validated_data.pop("login_password", "")
        staff_member = super().create(validated_data)
        return self._sync_employee_user(staff_member, login_username, login_password)

    @transaction.atomic
    def update(self, instance, validated_data):
        login_username = validated_data.pop("login_username", "")
        login_password = validated_data.pop("login_password", "")
        staff_member = super().update(instance, validated_data)
        if staff_member.user:
            staff_member.user.is_active = staff_member.is_active
            staff_member.user.save(update_fields=["is_active"])
            profile, _created = Profile.objects.get_or_create(user=staff_member.user)
            profile.role = Profile.ROLE_EMPLOYEE
            profile.business_client = staff_member.business_client
            profile.phone = staff_member.phone
            profile.save(update_fields=["role", "business_client", "phone", "updated_at"])
        return self._sync_employee_user(staff_member, login_username, login_password)


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
