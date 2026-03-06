import uuid

from django.conf import settings
from django.db import models

from src.apps.server.models import Channel


class Message(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(to=Channel, on_delete=models.CASCADE, related_name="messages")
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="messages"
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.channel.name}] {self.author.email}: {self.content[:30]}"
