from django import forms
from django.contrib import admin

from accounts.models import Profile


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


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    form = ProfileAdminForm
    list_display = ("user", "role", "phone", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "user__username", "phone")
    fieldsets = (
        ("Nalog", {"fields": ("user", "role", "phone")}),
    )
