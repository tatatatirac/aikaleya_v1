from django.contrib import admin

from ai_agent.models import AIIntent, AIToolRun


@admin.register(AIIntent)
class AIIntentAdmin(admin.ModelAdmin):
    list_display = ("business_client", "intent", "confidence", "language", "created_at")
    list_filter = ("business_client", "intent", "language")
    search_fields = ("input_text",)


@admin.register(AIToolRun)
class AIToolRunAdmin(admin.ModelAdmin):
    list_display = ("business_client", "tool_name", "status", "created_at")
    list_filter = ("business_client", "tool_name", "status")
    search_fields = ("error",)
