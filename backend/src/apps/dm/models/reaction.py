import uuid

from django.conf import settings
from django.db import models


class DMMessageReaction(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        "dm.DMMessage",
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dm_message_reactions",
    )
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"],
                name="dm_react_unique_message_user_emoji",
            )
        ]
        indexes = [
            models.Index(fields=["message", "emoji"], name="dm_react_msg_emoji_idx"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.emoji}:{self.message_id}"
