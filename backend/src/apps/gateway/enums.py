from django.db.models import TextChoices


class ModuleType(TextChoices):
    CHAT = ("CHAT", "chat")
    PRESENCE = ("PRESENCE", "presence")
    SYSTEM = ("SYSTEM", "system")


class ChatAction(TextChoices):
    SEND_MESSAGE = ("SEND_MESSAGE", "send_message")
