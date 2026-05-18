import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def client_logo_upload_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    if ext not in {"png", "jpg", "jpeg", "webp", "svg"}:
        ext = "png"
    return f"client_logos/client_{instance.id or 'new'}.{ext}"


class BusinessClient(models.Model):
    PACKAGE_BASIC = "basic"
    PACKAGE_PRO = "pro"
    PACKAGE_BUSINESS = "business"
    PACKAGE_BUSINESS_PLUS = "business_plus"
    PACKAGE_BUSINESS_PRO_PLUS = "business_pro_plus"
    PACKAGE_GOD_MODE = "god_mode"

    PACKAGE_CHOICES = (
        (PACKAGE_BASIC, "Basic"),
        (PACKAGE_PRO, "Pro"),
        (PACKAGE_BUSINESS, "Business"),
        (PACKAGE_BUSINESS_PLUS, "Business+"),
        (PACKAGE_BUSINESS_PRO_PLUS, "BusinessPro+"),
        (PACKAGE_GOD_MODE, "GOD MODE"),
    )

    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("es", "Spanish"),
        ("pt", "Portuguese"),
        ("ru", "Russian"),
        ("sr", "Serbian"),
        ("fr", "French"),
        ("it", "Italian"),
        ("de", "German"),
    )

    TIME_FORMAT_CHOICES = (
        ("24h", "24h"),
        ("12h", "AM/PM"),
    )

    DATE_FORMAT_CHOICES = (
        ("dd-mm-yyyy", "DD-MM-YYYY"),
        ("mm-dd-yyyy", "MM-DD-YYYY"),
    )

    WEEK_START_CHOICES = (
        (0, "Monday"),
        (6, "Sunday"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business_clients")
    name = models.CharField(max_length=160)
    public_name = models.CharField(max_length=160, blank=True)
    package = models.CharField(max_length=30, choices=PACKAGE_CHOICES, default=PACKAGE_BASIC)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en")
    interface_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en")
    voice_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default="en")
    timezone = models.CharField(max_length=80, default="Europe/Belgrade")
    is_demo = models.BooleanField(default=False)
    kaleya_enabled = models.BooleanField(default=True)
    work_start = models.TimeField(default="09:00")
    work_end = models.TimeField(default="16:00")
    slot_interval_minutes = models.PositiveIntegerField(default=30)
    time_format = models.CharField(max_length=10, choices=TIME_FORMAT_CHOICES, default="24h")
    date_format = models.CharField(max_length=20, choices=DATE_FORMAT_CHOICES, default="dd-mm-yyyy")
    week_start = models.IntegerField(choices=WEEK_START_CHOICES, default=0)
    allow_phone_calls = models.BooleanField(default=True)
    allow_sms = models.BooleanField(default=True)
    allow_whatsapp = models.BooleanField(default=True)
    allow_viber = models.BooleanField(default=True)
    allow_telegram = models.BooleanField(default=True)
    business_phone = models.CharField(max_length=40, blank=True, default="")
    business_email = models.EmailField(blank=True, default="")
    logo_image = models.FileField(upload_to=client_logo_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def clean(self):
        if self.work_end <= self.work_start:
            raise ValidationError({"work_end": "Kraj radnog vremena mora biti posle pocetka."})
        if self.slot_interval_minutes not in (15, 20, 30, 45, 60):
            raise ValidationError({"slot_interval_minutes": "Interval termina mora biti 15, 20, 30, 45 ili 60 minuta."})

    def __str__(self):
        return self.public_name or self.name


class ClientApiSettings(models.Model):
    business_client = models.OneToOneField(BusinessClient, on_delete=models.CASCADE, related_name="api_settings")
    ai_provider = models.CharField(max_length=80, default="openai")
    ai_model = models.CharField(max_length=120, default="gpt-4o-mini")
    ai_api_key = models.CharField(max_length=500, blank=True)
    voice_provider = models.CharField(max_length=80, default="elevenlabs")
    voice_model = models.CharField(max_length=120, blank=True)
    voice_api_key = models.CharField(max_length=500, blank=True)
    voice_id = models.CharField(max_length=160, blank=True)
    master_prompt = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"API settings: {self.business_client}"


class BusinessKnowledgeEntry(models.Model):
    CATEGORY_FAQ = "faq"
    CATEGORY_POLICY = "policy"
    CATEGORY_PRICING = "pricing"
    CATEGORY_LOCATION = "location"
    CATEGORY_PREPARATION = "preparation"
    CATEGORY_CUSTOM = "custom"

    CATEGORY_CHOICES = (
        (CATEGORY_FAQ, "FAQ"),
        (CATEGORY_POLICY, "Policy"),
        (CATEGORY_PRICING, "Pricing"),
        (CATEGORY_LOCATION, "Location"),
        (CATEGORY_PREPARATION, "Preparation"),
        (CATEGORY_CUSTOM, "Custom"),
    )

    business_client = models.ForeignKey(BusinessClient, on_delete=models.CASCADE, related_name="knowledge_entries")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default=CATEGORY_FAQ)
    language = models.CharField(max_length=10, choices=BusinessClient.LANGUAGE_CHOICES, default="en")
    title = models.CharField(max_length=180)
    answer = models.TextField()
    keywords = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("category", "title")
        indexes = [
            models.Index(fields=("business_client", "language", "category", "is_active")),
        ]

    def __str__(self):
        return f"{self.business_client} - {self.title}"


def get_active_client_for_user(user):
    if not user or not user.is_authenticated:
        return None
    return BusinessClient.objects.filter(owner=user).first()
