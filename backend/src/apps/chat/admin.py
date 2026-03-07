from django.contrib import admin

from .models import ChannelReadState, Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("uuid", "author", "channel", "content", "created_at")
    list_filter = ("channel", "author")
    search_fields = ("content",)
    readonly_fields = (
        "uuid",
        "created_at",
    )
    list_select_related = ("author", "channel")


@admin.register(ChannelReadState)
class ChannelReadStateAdmin(admin.ModelAdmin):
    list_display = ("uuid", "user", "channel", "last_read_message", "updated_at")
    list_filter = ("channel", "user")
    readonly_fields = ("uuid", "updated_at")
    list_select_related = ("user", "channel", "last_read_message")
