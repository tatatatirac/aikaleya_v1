from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from billing.models import Plan, Subscription
from clients.models import BusinessClient, ClientApiSettings


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        identifier = attrs.get("email", "").strip()
        password = attrs.get("password")

        user_obj = (
            User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username__iexact=identifier).first()
        )
        username = user_obj.username if user_obj else identifier.lower()

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Pogresan email ili lozinka.")
        if not user.is_active:
            raise serializers.ValidationError("Nalog nije aktivan.")

        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    phone = serializers.CharField(source="profile.phone", read_only=True)

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name", "role", "phone", "is_staff")


class AuthResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    user = UserSerializer()


class ClientRegistrationSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=40)
    company = serializers.CharField(max_length=160)
    full_name = serializers.CharField(max_length=160)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    country = serializers.CharField(max_length=80, required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_plan_code(self, value):
        code = value.strip().lower()
        try:
            plan = Plan.objects.get(code=code, active=True)
        except Plan.DoesNotExist as exc:
            raise serializers.ValidationError("Paket nije pronadjen.") from exc
        if plan.is_contact_only:
            raise serializers.ValidationError("Za ovaj paket je potreban kontakt sa prodajom.")
        return code

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError("Nalog sa ovim emailom vec postoji.")
        return email

    @transaction.atomic
    def create(self, validated_data):
        plan = Plan.objects.get(code=validated_data["plan_code"], active=True)
        full_name = validated_data["full_name"].strip()
        first_name, _, last_name = full_name.partition(" ")

        user = User(
            username=validated_data["email"],
            email=validated_data["email"],
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(validated_data["password"])
        user.save()

        user.profile.role = "client"
        user.profile.phone = validated_data.get("phone", "")
        user.profile.save(update_fields=["role", "phone", "updated_at"])

        client = BusinessClient.objects.create(
            owner=user,
            name=validated_data["company"],
            public_name=validated_data["company"],
            package=plan.code,
            language="en",
            interface_language="en",
            voice_language="en",
            timezone="Europe/Belgrade",
            kaleya_enabled=True,
        )
        user.profile.business_client = client
        user.profile.save(update_fields=["business_client", "updated_at"])

        ClientApiSettings.objects.get_or_create(
            business_client=client,
            defaults={
                "ai_provider": "anthropic",
                "ai_model": "claude-haiku-4-5-20251001",
                "voice_provider": "elevenlabs",
                "voice_model": "eleven_multilingual_v2",
            },
        )
        Subscription.objects.create(
            business_client=client,
            plan=plan,
            status=Subscription.STATUS_TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=plan.trial_days),
        )

        try:
            send_mail(
                subject="Welcome to Kaleya — your AI receptionist is ready",
                message=(
                    f"Hi {first_name or user.username},\n\n"
                    f"Welcome to Kaleya! Your account is set up and your {plan.trial_days}-day free trial has started.\n\n"
                    f"Log in at aikaleya.com, then set up your business profile, working hours, and staff "
                    f"so Kaleya knows how to handle your calls and messages.\n\n"
                    f"Questions? We're at hello@aikaleya.com.\n\n"
                    f"— The Kaleya Team\n"
                    f"aikaleya.com"
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return {"user": user, "client": client, "plan": plan}
