from django.contrib import admin

from .models import Message


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
