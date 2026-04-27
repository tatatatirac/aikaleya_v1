from django.contrib import admin

from communications.models import CallSession, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("business_client", "customer", "channel", "status", "language", "last_message_at")
    list_filter = ("business_client", "channel", "status", "language")
    search_fields = ("customer__first_name", "customer__last_name", "external_thread_id")
    inlines = (MessageInline,)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "direction", "message_type", "sender_label", "created_at")
    list_filter = ("direction", "message_type", "conversation__business_client")
    search_fields = ("body", "sender_label", "provider_message_id")


@admin.register(CallSession)
class CallSessionAdmin(admin.ModelAdmin):
    list_display = ("business_client", "provider", "from_number", "to_number", "status", "created_at")
    list_filter = ("business_client", "provider", "status")
    search_fields = ("from_number", "to_number", "external_call_id", "transcript")
