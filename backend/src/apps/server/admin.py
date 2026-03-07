from django.contrib import admin

# Pamiętaj o zaimportowaniu nowych modeli!
from .models import Channel, Server, Role, ServerMember

class ChannelInline(admin.TabularInline):
    model = Channel
    extra = 1
    fields = ('name', 'channel_type', 'is_public', 'topic')


class ServerMemberInline(admin.TabularInline):
    model = ServerMember
    extra = 1
    fields = ('user',)


class RoleInline(admin.TabularInline):
    model = Role
    extra = 1


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "owner", "created_at")
    list_select_related = ("owner",)
    readonly_fields = (
        "uuid",
        "created_at",
    )
    inlines = [RoleInline, ChannelInline, ServerMemberInline]


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "server", "channel_type", "is_public")
    list_filter = ("server", "channel_type", "is_public")
    readonly_fields = (
        "uuid",
        "created_at",
    )
    list_select_related = ("server",)

    filter_horizontal = ("allowed_roles",)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("uuid", "name", "server")
    list_filter = ("server",)
    readonly_fields = ("uuid",)
    list_select_related = ("server",)


@admin.register(ServerMember)
class ServerMemberAdmin(admin.ModelAdmin):
    list_display = ("uuid", "user", "server", "joined_at")
    list_filter = ("server",)
    readonly_fields = ("uuid", "joined_at")
    list_select_related = ("user", "server")

    filter_horizontal = ("roles",)
