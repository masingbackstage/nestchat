from django.contrib import admin

from src.apps.profile.models import Profile

from .models import CustomUser


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Profile Info"
    readonly_fields = ("tag",)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("email", "is_staff", "is_active")
    inlines = (ProfileInline,)
