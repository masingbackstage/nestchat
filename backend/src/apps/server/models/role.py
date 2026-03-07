import uuid
from django.db import models


class Role(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    server = models.ForeignKey('server.Server', on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.server.name})"