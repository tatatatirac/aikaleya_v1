from django import forms
from django.contrib import admin

from billing.models import CheckoutSession, Plan, Subscription


class PlanAdminForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ("code", "name", "monthly_price", "currency", "trial_days", "is_contact_only", "description", "features", "active")
        labels = {
            "code": "Kod paketa",
            "name": "Naziv paketa",
            "monthly_price": "Mesečna cena",
            "currency": "Valuta",
            "trial_days": "Probni period",
            "is_contact_only": "Samo kontakt",
            "description": "Opis",
            "features": "Lista mogućnosti",
            "active": "Aktivan",
        }
        help_texts = {
            "features": "JSON lista mogućnosti. Primer: [\"AI zakazivanje\", \"Kalendar\"].",
            "is_contact_only": "Uključi za GOD MODE ako ne ide direktno plaćanje nego kontakt.",
        }


class SubscriptionAdminForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ("business_client", "plan", "status", "trial_ends_at", "current_period_start", "current_period_end")
        labels = {
            "business_client": "Klijent",
            "plan": "Paket",
            "status": "Status",
            "trial_ends_at": "Probni period do",
            "current_period_start": "Period od",
            "current_period_end": "Period do",
        }


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    form = PlanAdminForm
    list_display = ("name", "code", "monthly_price", "currency", "trial_days", "active")
    list_filter = ("active", "is_contact_only", "currency")
    search_fields = ("name", "code")
    fieldsets = (
        ("Paket", {"fields": ("code", "name", "monthly_price", "currency", "trial_days", "is_contact_only", "active")}),
        ("Opis", {"fields": ("description", "features")}),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    form = SubscriptionAdminForm
    list_display = ("business_client", "plan", "status", "trial_ends_at", "current_period_end")
    list_filter = ("status", "plan")
    search_fields = ("business_client__name", "external_customer_id", "external_subscription_id")
    fieldsets = (
        ("Pretplata", {"fields": ("business_client", "plan", "status")}),
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
        ("Zahtev", {"fields": ("plan", "provider", "status", "business_client")}),
        ("Kontakt", {"fields": ("email", "company", "full_name")}),
        ("Placanje", {"fields": ("amount", "currency", "trial_days", "checkout_url", "external_checkout_id")}),
        ("Sistem", {"fields": ("metadata", "created_at", "updated_at")}),
    )
