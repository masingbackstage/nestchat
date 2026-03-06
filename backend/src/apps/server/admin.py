from django.contrib import admin

from .models import Channel, Server


class ChannelInline(admin.TabularInline):
    model = Channel
    extra = 1


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "owner", "created_at")
    list_select_related = ("owner",)
    readonly_fields = (
        "uuid",
        "created_at",
    )
    inlines = [ChannelInline]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "server", "channel_type")
    list_filter = ("server", "channel_type")
    readonly_fields = (
        "uuid",
        "created_at",
    )
    list_select_related = ("server",)
