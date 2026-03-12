import uuid

from django.conf import settings
from django.db import models


class DMConversation(models.Model):
    TYPE_DIRECT = "DIRECT"
    TYPE_GROUP = "GROUP"
    TYPE_CHOICES = [
        (TYPE_DIRECT, "Direct"),
        (TYPE_GROUP, "Group"),
    ]

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120, blank=True, null=True)
    avatar = models.ImageField(upload_to="dm_avatars/", blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_dm_conversations",
        null=True,
        blank=True,
    )
    direct_key = models.CharField(max_length=128, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="dm.DMConversationParticipant",
        related_name="dm_conversations",
    )

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.conversation_type}:{self.uuid}"
