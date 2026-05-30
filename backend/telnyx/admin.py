from django.contrib import admin

from telnyx.models import TelnyxPhoneNumber


@admin.register(TelnyxPhoneNumber)
class TelnyxPhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "business_client", "country_code", "voice_enabled", "sms_enabled", "is_active", "purchased_at")
    list_filter = ("country_code", "voice_enabled", "sms_enabled", "is_active")
    search_fields = ("phone_number", "business_client__name")
    raw_id_fields = ("business_client",)
