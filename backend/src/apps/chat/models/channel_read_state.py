import uuid

from django.conf import settings
from django.db import models

from src.apps.chat.models.message import Message
from src.apps.server.models import Channel


class ChannelReadState(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="channel_read_states"
    )
    channel = models.ForeignKey(to=Channel, on_delete=models.CASCADE, related_name="read_states")
    last_read_message = models.ForeignKey(
        to=Message,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "channel"], name="chat_read_state_unique_user_channel"
            )
        ]

    def __str__(self):
        return f"{self.user_id}:{self.channel_id}"
