import uuid

from django.conf import settings
from django.db import models


class DMConversationParticipant(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "dm.DMConversation",
        on_delete=models.CASCADE,
        related_name="conversation_participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dm_participations",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey(
        "dm.DMMessage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="read_by_participants",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="dm_participant_unique_conversation_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "conversation"], name="dm_part_user_conv_idx"),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.conversation_id}"
