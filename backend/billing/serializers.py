from rest_framework import serializers

from billing.models import CheckoutSession, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = (
            "id",
            "code",
            "name",
            "monthly_price",
            "currency",
            "trial_days",
            "is_contact_only",
            "max_staff_members",
            "allow_whatsapp",
            "allow_viber",
            "allow_telegram",
            "allow_sms",
            "allow_phone_calls",
            "allow_instagram_dm",
            "allow_tiktok_dm",
            "allow_client_api_override",
            "allow_more_languages_by_agreement",
            "includes_elevenlabs_voice",
            "description",
            "features",
            "active",
            "sort_order",
        )
        read_only_fields = ("id",)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True, required=False)
    trial_is_active = serializers.BooleanField(read_only=True)
    trial_days_left = serializers.IntegerField(read_only=True)
    is_access_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_id",
            "status",
            "trial_ends_at",
            "trial_is_active",
            "trial_days_left",
            "is_access_active",
            "current_period_start",
            "current_period_end",
            "external_customer_id",
            "external_subscription_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CheckoutSessionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)

    class Meta:
        model = CheckoutSession
        fields = (
            "id",
            "business_client",
            "plan",
            "provider",
            "status",
            "email",
            "company",
            "full_name",
            "amount",
            "currency",
            "trial_days",
            "checkout_url",
            "external_checkout_id",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CheckoutSessionCreateSerializer(serializers.Serializer):
    plan_code = serializers.ChoiceField(choices=[code for code, _label in Plan.CODE_CHOICES])
    email = serializers.EmailField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True, max_length=160)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)
