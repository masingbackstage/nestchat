from django.contrib import admin

from src.apps.friends.models import Friendship


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("uuid", "requester", "addressee", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("requester__email", "addressee__email")
