from rest_framework import serializers

from billing.models import Plan, Subscription


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
            "description",
            "features",
            "active",
            "sort_order",
        )
        read_only_fields = ("id",)


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "plan_id",
            "status",
            "trial_ends_at",
            "current_period_start",
            "current_period_end",
            "external_customer_id",
            "external_subscription_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

