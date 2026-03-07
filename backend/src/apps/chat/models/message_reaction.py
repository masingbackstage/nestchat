import uuid

from django.conf import settings
from django.db import models


class MessageReaction(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        "chat.Message",
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_reactions",
    )
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"],
                name="chat_react_unique_message_user_emoji",
            )
        ]
        indexes = [
            models.Index(fields=["message", "emoji"], name="chat_react_msg_emoji_idx"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.emoji}:{self.message_id}"
