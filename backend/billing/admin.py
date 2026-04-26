from django.contrib import admin

from billing.models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "monthly_price", "currency", "trial_days", "active", "sort_order")
    list_filter = ("active", "is_contact_only", "currency")
    search_fields = ("name", "code")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("business_client", "plan", "status", "trial_ends_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("business_client__name", "external_customer_id", "external_subscription_id")

