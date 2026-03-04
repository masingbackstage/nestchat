from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'display_name', 'tag', 'is_online',)
    list_filter = ('is_online',)
    search_fields = ('user__email', 'display_name', 'tag',)
    readonly_fields = ('tag', 'is_online',)
    list_select_related = ('user',)
    fieldsets = (
        ('Personal', {
            'fields': ('user', 'display_name', 'tag',)
        }),
        ('Customization', {
            'fields': ('avatar', 'bio', 'custom_status', 'theme_color',)
        }),
        ('Status', {
            'fields': ('is_online',)
        }),
    )

    def get_username(self, obj):
        return obj.user.email

    get_username.short_description = 'User Email'