import random
from uuid import uuid4

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from src import settings
from src.apps.user.models import CustomUser


class Profile(models.Model):
    uuid = models.UUIDField(default=uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    display_name = models.CharField(max_length=50, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    tag = models.CharField(max_length=4, editable=False)
    custom_status = models.CharField(max_length=100, blank=True)
    theme_color = models.CharField(max_length=7, default="#508991")

    is_online = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.tag:
            self.tag = f"{random.randint(1, 9999):04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        name = self.display_name or self.user.email.split("@")[0]
        return f"{name}#{self.tag}"


@receiver(post_save, sender=CustomUser)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Creates a profile for a new user or saves the existing one.
    This ensures that every user has a profile.
    """
    profile, _ = Profile.objects.get_or_create(user=instance)
