import uuid

from django.db import models


class ServerEmoji(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey("server.Server", on_delete=models.CASCADE, related_name="emojis")
    name = models.SlugField(max_length=50)
    image = models.ImageField(upload_to="server_emojis/")
    is_animated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["server", "name"],
                name="server_emoji_unique_name_per_server",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.server_id}:{self.name}"
