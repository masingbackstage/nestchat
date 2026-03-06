from django.db.models import TextChoices


class ChannelType(TextChoices):
    TEXT = (
        "TEXT",
        "text",
    )
    VOICE = (
        "VOICE",
        "voice",
    )
