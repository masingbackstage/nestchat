from dataclasses import dataclass

from src.apps.dm.models import DMMessage
from src.apps.dm.services.conversation_permissions import (
    DMConversationNotFound,
    DMConversationPermissionDenied,
    get_dm_conversation_for_user_or_raise,
)


@dataclass(slots=True)
class DMMessagePermissionError(Exception):
    detail: str
    code: str


class DMMessageNotFound(DMMessagePermissionError):
    pass


class DMMessagePermissionDenied(DMMessagePermissionError):
    pass


def get_dm_message_for_user_or_raise(user, message_uuid):
    try:
        message = (
            DMMessage.objects.select_related("conversation", "author")
            .prefetch_related("conversation__conversation_participants")
            .get(uuid=message_uuid)
        )
    except DMMessage.DoesNotExist as exc:
        raise DMMessageNotFound(detail="Message not found.", code="not_found") from exc

    try:
        get_dm_conversation_for_user_or_raise(user, message.conversation.uuid)
    except DMConversationNotFound as exc:
        raise DMMessageNotFound(detail=exc.detail, code=exc.code) from exc
    except DMConversationPermissionDenied as exc:
        raise DMMessagePermissionDenied(detail=exc.detail, code=exc.code) from exc

    return message


def can_edit_or_delete_dm_message(user, message: DMMessage) -> bool:
    return message.author_id == user.pk
