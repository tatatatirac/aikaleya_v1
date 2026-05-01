import uuid
from math import ceil

from django.db import models
from django.utils import timezone

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
    max_staff_members = models.PositiveIntegerField(null=True, blank=True)
    allow_whatsapp = models.BooleanField(default=True)
    allow_viber = models.BooleanField(default=True)
    allow_telegram = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=False)
    allow_phone_calls = models.BooleanField(default=False)
    allow_instagram_dm = models.BooleanField(default=False)
    allow_tiktok_dm = models.BooleanField(default=False)
    allow_client_api_override = models.BooleanField(default=False)
    allow_more_languages_by_agreement = models.BooleanField(default=False)
    includes_elevenlabs_voice = models.BooleanField(default=False)
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

    @property
    def trial_is_active(self):
        if self.status != self.STATUS_TRIAL:
            return False
        if not self.trial_ends_at:
            return True
        return self.trial_ends_at >= timezone.now()

    @property
    def trial_days_left(self):
        if self.status != self.STATUS_TRIAL or not self.trial_ends_at:
            return 0
        remaining = self.trial_ends_at - timezone.now()
        if remaining.total_seconds() <= 0:
            return 0
        return ceil(remaining.total_seconds() / 86400)

    @property
    def is_access_active(self):
        if self.status == self.STATUS_ACTIVE:
            return True
        return self.trial_is_active


class CheckoutSession(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PROVIDER_PENDING = "provider_pending"
    STATUS_MANUAL_CONTACT = "manual_contact"
    STATUS_PAID = "paid"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PROVIDER_PENDING, "Provider pending"),
        (STATUS_MANUAL_CONTACT, "Manual contact"),
        (STATUS_PAID, "Paid"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    )

    PROVIDER_MANUAL = "manual"
    PROVIDER_STRIPE = "stripe"
    PROVIDER_PAYPAL = "paypal"
    PROVIDER_LEMONSQUEEZY = "lemonsqueezy"

    PROVIDER_CHOICES = (
        (PROVIDER_MANUAL, "Manual"),
        (PROVIDER_LEMONSQUEEZY, "Lemon Squeezy"),
        (PROVIDER_PAYPAL, "PayPal"),
        (PROVIDER_STRIPE, "Stripe"),
    )

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    business_client = models.ForeignKey(
        BusinessClient,
        on_delete=models.SET_NULL,
        related_name="checkout_sessions",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="checkout_sessions")
    provider = models.CharField(max_length=40, choices=PROVIDER_CHOICES, default=PROVIDER_MANUAL)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    email = models.EmailField(blank=True)
    company = models.CharField(max_length=160, blank=True)
    full_name = models.CharField(max_length=160, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="USD")
    trial_days = models.PositiveIntegerField(default=14)
    checkout_url = models.URLField(blank=True)
    external_checkout_id = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.plan} - {self.email or self.company or self.status}"


class PendingCheckoutRegistration(models.Model):
    checkout = models.OneToOneField(
        CheckoutSession,
        on_delete=models.CASCADE,
        related_name="pending_registration",
    )
    email = models.EmailField()
    company = models.CharField(max_length=160)
    full_name = models.CharField(max_length=160)
    password_hash = models.CharField(max_length=256)
    phone = models.CharField(max_length=40, blank=True)
    country = models.CharField(max_length=80, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Pending registration: {self.email}"
