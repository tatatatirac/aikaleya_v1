from django.db import models

from clients.models import BusinessClient


class Plan(models.Model):
    CODE_BASIC = "basic"
    CODE_PRO = "pro"
    CODE_BUSINESS = "business"
    CODE_BUSINESS_PLUS = "business_plus"
    CODE_BUSINESS_PRO_PLUS = "business_pro_plus"
    CODE_GOD_MODE = "god_mode"

    CODE_CHOICES = (
        (CODE_BASIC, "Basic"),
        (CODE_PRO, "Pro"),
        (CODE_BUSINESS, "Business"),
        (CODE_BUSINESS_PLUS, "Business+"),
        (CODE_BUSINESS_PRO_PLUS, "BusinessPro+"),
        (CODE_GOD_MODE, "GOD MODE"),
    )

    code = models.CharField(max_length=40, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=80)
    monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="EUR")
    trial_days = models.PositiveIntegerField(default=14)
    is_contact_only = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("sort_order", "monthly_price")

    def __str__(self):
        return self.name


class Subscription(models.Model):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    business_client = models.OneToOneField(BusinessClient, on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    external_customer_id = models.CharField(max_length=160, blank=True)
    external_subscription_id = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business_client} - {self.plan}"
