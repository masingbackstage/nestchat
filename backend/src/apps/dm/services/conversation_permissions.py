from dataclasses import dataclass

from src.apps.dm.models import DMConversation


@dataclass(slots=True)
class DMConversationPermissionError(Exception):
    detail: str
    code: str


class DMConversationNotFound(DMConversationPermissionError):
    pass


class DMConversationPermissionDenied(DMConversationPermissionError):
    pass


def get_dm_conversation_for_user_or_raise(user, conversation_uuid):
    try:
        conversation = DMConversation.objects.prefetch_related(
            "conversation_participants__user",
            "conversation_participants__user__profile",
        ).get(uuid=conversation_uuid)
    except DMConversation.DoesNotExist as exc:
        raise DMConversationNotFound(detail="Conversation not found.", code="not_found") from exc

    is_participant = conversation.conversation_participants.filter(user=user).exists()
    if not is_participant:
        raise DMConversationPermissionDenied(detail="Permission denied.", code="permission_denied")

    return conversation
