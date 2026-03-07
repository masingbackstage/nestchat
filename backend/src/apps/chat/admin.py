from django.contrib import admin

from .models import ChannelReadState, Message, MessageReaction


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("uuid", "author", "channel", "is_deleted", "created_at")
    list_filter = ("channel", "author", "is_deleted")
    search_fields = ("content",)
    readonly_fields = (
        "uuid",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    list_select_related = ("author", "channel", "deleted_by")


@admin.register(ChannelReadState)
class ChannelReadStateAdmin(admin.ModelAdmin):
    list_display = ("uuid", "user", "channel", "last_read_message", "updated_at")
    list_filter = ("channel", "user")
    readonly_fields = ("uuid", "updated_at")
    list_select_related = ("user", "channel", "last_read_message")


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ("uuid", "message", "user", "emoji", "created_at")
    list_filter = ("emoji", "created_at")
    search_fields = ("emoji",)
    readonly_fields = ("uuid", "created_at")
    list_select_related = ("message", "user")
