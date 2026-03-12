import uuid

from django.conf import settings
from django.db import models


class Friendship(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        CANCELED = "CANCELED", "Canceled"

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_low = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_low",
    )
    user_high = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friendships_as_high",
    )

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friend_requests_sent",
    )
    addressee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="friend_requests_received",
    )

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    responded_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_low", "user_high"],
                name="friends_unique_user_pair",
            )
        ]
        indexes = [
            models.Index(fields=["requester", "status"], name="friends_req_status_idx"),
            models.Index(fields=["addressee", "status"], name="friends_add_status_idx"),
        ]

    def __str__(self):
        return f"{self.requester_id}->{self.addressee_id}:{self.status}"

    @staticmethod
    def normalize_pair(user_a, user_b):
        if str(user_a.uuid) <= str(user_b.uuid):
            return user_a, user_b
        return user_b, user_a

    @classmethod
    def pair_queryset(cls, user_a, user_b):
        low, high = cls.normalize_pair(user_a, user_b)
        return cls.objects.filter(user_low=low, user_high=high)

    def counterpart_for(self, user):
        if self.user_low_id == user.pk:
            return self.user_high
        return self.user_low
