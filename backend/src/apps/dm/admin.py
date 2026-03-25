from django.contrib import admin

from src.apps.dm.models import (
    DMConversation,
    DMConversationParticipant,
    DMMessage,
    DMMessageReaction,
)


@admin.register(DMConversation)
class DMConversationAdmin(admin.ModelAdmin):
    list_display = ("uuid", "conversation_type", "title", "created_by", "updated_at")
    search_fields = ("uuid", "title")


@admin.register(DMConversationParticipant)
class DMConversationParticipantAdmin(admin.ModelAdmin):
    list_display = ("uuid", "conversation", "user", "joined_at")
    search_fields = ("uuid",)


@admin.register(DMMessage)
class DMMessageAdmin(admin.ModelAdmin):
    list_display = ("uuid", "conversation", "author", "is_deleted", "created_at")
    search_fields = ("uuid", "content")


@admin.register(DMMessageReaction)
class DMMessageReactionAdmin(admin.ModelAdmin):
    list_display = ("uuid", "message", "user", "emoji", "created_at")
    search_fields = ("emoji",)
