import uuid

from django.conf import settings
from django.db import models


class VoiceChannelOccupant(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey(
        "server.Server", on_delete=models.CASCADE, related_name="voice_channel_occupants"
    )
    channel = models.ForeignKey(
        "server.Channel", on_delete=models.CASCADE, related_name="voice_occupants"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="voice_channel_occupancies"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["server", "user"],
                name="voice_occupant_unique_server_user",
            )
        ]
        ordering = ["created_at", "user_id"]

    def __str__(self):
        return f"{self.server_id}:{self.channel_id}:{self.user_id}"
