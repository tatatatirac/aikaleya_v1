from rest_framework import serializers

from billing.models import CheckoutSession, PaymentWebhookEvent, Plan, Subscription


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
            "public_id",
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
    _YEARLY_SKIP = {"god_mode"}
    plan_code = serializers.ChoiceField(choices=(
        [code for code, _label in Plan.CODE_CHOICES]
        + [f"{code}_yearly" for code, _label in Plan.CODE_CHOICES if code not in _YEARLY_SKIP]
    ))
    email = serializers.EmailField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True, max_length=160)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=160)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8, trim_whitespace=False, write_only=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=40)
    country = serializers.CharField(required=False, allow_blank=True, max_length=80)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


class PaymentWebhookEventSerializer(serializers.ModelSerializer):
    checkout_public_id = serializers.SerializerMethodField()

    class Meta:
        model = PaymentWebhookEvent
        fields = (
            "id",
            "provider",
            "event_name",
            "external_event_id",
            "external_object_id",
            "checkout",
            "checkout_public_id",
            "status",
            "signature_valid",
            "payload",
            "raw_body",
            "error",
            "processed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_checkout_public_id(self, obj):
        return str(obj.checkout.public_id) if obj.checkout_id else ""
