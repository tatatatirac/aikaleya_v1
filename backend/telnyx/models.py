from django.db import models

from clients.models import BusinessClient


class TelnyxPhoneNumber(models.Model):
    """Maps a Telnyx phone number to a BusinessClient (salon)."""

    COUNTRY_US = "US"
    COUNTRY_CA = "CA"
    COUNTRY_CHOICES = (
        ("US", "United States"),
        ("CA", "Canada"),
        ("GB", "United Kingdom"),
        ("RS", "Serbia"),
        ("HR", "Croatia"),
        ("BA", "Bosnia"),
        ("ME", "Montenegro"),
        ("OTHER", "Other"),
    )

    business_client = models.ForeignKey(
        BusinessClient,
        on_delete=models.CASCADE,
        related_name="telnyx_numbers",
    )
    phone_number = models.CharField(
        max_length=30,
        unique=True,
        help_text="E.164 format, e.g. +12364773103",
    )
    country_code = models.CharField(max_length=10, choices=COUNTRY_CHOICES, default=COUNTRY_US)
    voice_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    telnyx_number_id = models.CharField(max_length=80, blank=True, help_text="Telnyx internal number ID")
    purchased_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-purchased_at",)
        indexes = [models.Index(fields=("phone_number",))]

    def __str__(self):
        return f"{self.phone_number} → {self.business_client}"


def business_client_for_number(phone_number: str):
    """
    Look up a BusinessClient by their Telnyx phone number.
    Returns None if not found.
    """
    if not phone_number:
        return None
    entry = (
        TelnyxPhoneNumber.objects.select_related("business_client")
        .filter(phone_number=phone_number, is_active=True)
        .first()
    )
    if entry:
        return entry.business_client

    # Fallback for development: try normalizing (strip +1, etc.)
    digits = "".join(c for c in phone_number if c.isdigit())
    entry = (
        TelnyxPhoneNumber.objects.select_related("business_client")
        .filter(phone_number__endswith=digits[-10:], is_active=True)
        .first()
    )
    return entry.business_client if entry else None
