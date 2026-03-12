import uuid

from django.conf import settings
from django.db import models


class DMMessage(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "dm.DMConversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dm_messages",
    )

    content = models.TextField(blank=True, default="")
    edited_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="deleted_dm_messages",
        blank=True,
        null=True,
    )

    # Crypto-ready v1 envelope fields.
    ciphertext = models.TextField(blank=True, null=True)
    nonce = models.CharField(max_length=255, blank=True, null=True)
    encryption_version = models.CharField(max_length=32, blank=True, null=True)
    sender_key_id = models.CharField(max_length=128, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "uuid"]
        indexes = [
            models.Index(
                fields=["conversation", "created_at", "uuid"],
                name="dm_msg_conv_created_uuid_idx",
            )
        ]

    def __str__(self):
        return f"{self.conversation_id}:{self.author_id}:{self.uuid}"
