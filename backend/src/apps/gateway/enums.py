from django.db.models import TextChoices


class ModuleType(TextChoices):
    CHAT = ("CHAT", "chat")
    PRESENCE = ("PRESENCE", "presence")
    SYSTEM = ("SYSTEM", "system")


class ChatAction(TextChoices):
    SEND_MESSAGE = ("SEND_MESSAGE", "send_message")
    JOIN_CHANNEL = ("JOIN_CHANNEL", "join_channel")
    EDIT_MESSAGE = ("EDIT_MESSAGE", "edit_message")
    DELETE_MESSAGE = ("DELETE_MESSAGE", "delete_message")
