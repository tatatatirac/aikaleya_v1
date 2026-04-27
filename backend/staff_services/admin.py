from django.contrib import admin

from staff_services.models import BlockedTime, Service, StaffMember, StaffService, WorkingHours


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("full_name", "business_client", "role_title", "phone", "is_active")
    list_filter = ("business_client", "is_active")
    search_fields = ("full_name", "phone", "email")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "business_client", "duration_minutes", "price", "currency", "is_active")
    list_filter = ("business_client", "is_active", "currency")
    search_fields = ("name", "category")


@admin.register(StaffService)
class StaffServiceAdmin(admin.ModelAdmin):
    list_display = ("staff_member", "service", "is_active")
    list_filter = ("is_active", "service__business_client")


@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    list_display = ("business_client", "staff_member", "weekday", "start_time", "end_time", "is_closed")
    list_filter = ("business_client", "weekday", "is_closed")


@admin.register(BlockedTime)
class BlockedTimeAdmin(admin.ModelAdmin):
    list_display = ("business_client", "staff_member", "start_at", "end_at", "reason")
    list_filter = ("business_client", "staff_member")
