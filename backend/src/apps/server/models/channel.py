import uuid

from django.db import models

from src.apps.server.enums import ChannelType


class Channel(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey('server.Server', on_delete=models.CASCADE, related_name="channels")
    name = models.CharField(max_length=100)
    topic = models.CharField(max_length=255, blank=True, null=True)
    channel_type = models.CharField(
        choices=ChannelType.choices, max_length=5, default=ChannelType.TEXT
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.server.name} # {self.name}"
