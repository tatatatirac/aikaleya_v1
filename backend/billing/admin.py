from django import forms
from django.contrib import admin

from billing.models import CheckoutSession, PaymentWebhookEvent, PendingCheckoutRegistration, Plan, Subscription


class PlanAdminForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ("code", "name", "monthly_price", "currency", "trial_days", "is_contact_only", "description", "features", "active")
        labels = {
            "code": "Plan code",
            "name": "Plan name",
            "monthly_price": "Monthly price",
            "currency": "Currency",
            "trial_days": "Trial period",
            "is_contact_only": "Contact only",
            "description": "Description",
            "features": "Features list",
            "active": "Active",
        }
        help_texts = {
            "features": 'JSON list of features. Example: ["AI booking", "Calendar"].',
            "is_contact_only": "Enable for GOD MODE if direct payment is not available and contact is needed instead.",
        }


class SubscriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ("business_client", "plan", "status", "trial_ends_at", "current_period_start", "current_period_end")
        labels = {
            "business_client": "Client",
            "plan": "Plan",
            "status": "Status",
            "trial_ends_at": "Trial ends at",
            "current_period_start": "Period from",
            "current_period_end": "Period to",
        }


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    form = PlanAdminForm
    list_display = ("name", "code", "monthly_price", "currency", "trial_days", "active")
    list_filter = ("active", "is_contact_only", "currency")
    search_fields = ("name", "code")
    fieldsets = (
        ("Plan", {"fields": ("code", "name", "monthly_price", "currency", "trial_days", "is_contact_only", "active")}),
        ("Description", {"fields": ("description", "features")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionAdminForm
    list_display = ("business_client", "plan", "status", "trial_ends_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("business_client__name", "external_customer_id", "external_subscription_id")
    fieldsets = (
        ("Subscription", {"fields": ("business_client", "plan", "status")}),
        ("Period", {"fields": ("trial_ends_at", "current_period_start", "current_period_end")}),
    )


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(admin.ModelAdmin):
    list_display = ("plan", "email", "company", "provider", "status", "amount", "currency", "created_at")
    list_filter = ("provider", "status", "plan", "currency")
    search_fields = ("email", "company", "full_name", "external_checkout_id")
    readonly_fields = (
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
    fieldsets = (
        ("Request", {"fields": ("plan", "provider", "status", "business_client")}),
        ("Contact", {"fields": ("email", "company", "full_name")}),
        ("Payment", {"fields": ("amount", "currency", "trial_days", "checkout_url", "external_checkout_id")}),
        ("System", {"fields": ("metadata", "created_at", "updated_at")}),
    )


@admin.register(PendingCheckoutRegistration)
class PendingCheckoutRegistrationAdmin(admin.ModelAdmin):
    list_display = ("email", "company", "checkout", "activated_at", "created_at")
    list_filter = ("activated_at", "created_at")
    search_fields = ("email", "company", "full_name", "checkout__external_checkout_id")
    readonly_fields = (
        "checkout",
        "email",
        "company",
        "full_name",
        "phone",
        "country",
        "password_hash",
        "activated_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Registration", {"fields": ("checkout", "email", "company", "full_name", "phone", "country")}),
        ("System", {"fields": ("password_hash", "activated_at", "created_at", "updated_at")}),
    )


@admin.register(PaymentWebhookEvent)
class PaymentWebhookEventAdmin(admin.ModelAdmin):
    list_display = (
        "provider",
        "event_name",
        "status",
        "signature_valid",
        "external_object_id",
        "checkout",
        "processed_at",
        "created_at",
    )
    list_filter = ("provider", "event_name", "status", "signature_valid", "created_at")
    search_fields = ("event_name", "external_event_id", "external_object_id", "checkout__email", "checkout__company")
    readonly_fields = (
        "provider",
        "event_name",
        "external_event_id",
        "external_object_id",
        "checkout",
        "status",
        "signature_valid",
        "payload",
        "raw_body",
        "error",
        "processed_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Webhook", {"fields": ("provider", "event_name", "status", "signature_valid")}),
        ("Links", {"fields": ("checkout", "external_event_id", "external_object_id")}),
        ("Processing", {"fields": ("processed_at", "error")}),
        ("Data", {"fields": ("payload", "raw_body")}),
        ("System", {"fields": ("created_at", "updated_at")}),
    )
