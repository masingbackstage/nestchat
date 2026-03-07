import uuid

from django.conf import settings
from django.db import models


class ServerMember(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="server_profiles"
    )
    server = models.ForeignKey(
        "server.Server", on_delete=models.CASCADE, related_name="server_members"
    )

    roles = models.ManyToManyField("server.Role", blank=True, related_name="members")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "server"]

    def __str__(self):
        return f"User {self.user_id} on {self.server.name}"
