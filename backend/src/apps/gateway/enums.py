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
    TOGGLE_REACTION = ("TOGGLE_REACTION", "toggle_reaction")
    JOIN_DM_CONVERSATION = ("JOIN_DM_CONVERSATION", "join_dm_conversation")
    SEND_DM_MESSAGE = ("SEND_DM_MESSAGE", "send_dm_message")
    EDIT_DM_MESSAGE = ("EDIT_DM_MESSAGE", "edit_dm_message")
    DELETE_DM_MESSAGE = ("DELETE_DM_MESSAGE", "delete_dm_message")
    TOGGLE_DM_REACTION = ("TOGGLE_DM_REACTION", "toggle_dm_reaction")
