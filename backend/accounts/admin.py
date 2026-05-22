from django import forms
from django.contrib import admin

from accounts.models import AccountSetupToken, Profile


class ProfileAdminForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("user", "role", "phone")
        labels = {
            "user": "Korisnik",
            "role": "Uloga",
            "phone": "Telefon",
        }
        help_texts = {
            "role": "Admin vidi sve. Client vidi samo svoje podatke.",
            "phone": "Opcioni kontakt telefon naloga.",
        }


@admin.register(AccountSetupToken)
class AccountSetupTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "token_short", "expires_at", "used_at", "is_valid_display", "created_at")
    list_filter = ("used_at",)
    search_fields = ("user__email", "token")
    readonly_fields = ("token", "created_at")

    @admin.display(description="Token (first 12)")
    def token_short(self, obj):
        return obj.token[:12] + "…"

    @admin.display(description="Valid?", boolean=True)
    def is_valid_display(self, obj):
        return obj.is_valid


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ("user", "role", "phone", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__username", "phone")
    fieldsets = (
        ("Nalog", {"fields": ("user", "role", "phone")}),
    )
