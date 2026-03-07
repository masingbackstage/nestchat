from dataclasses import dataclass

from src.apps.chat.models import Message
from src.apps.chat.services.channel_permissions import (
    ChannelNotFound,
    ChannelPermissionDenied,
    get_channel_for_user_or_raise,
)


@dataclass(slots=True)
class MessagePermissionError(Exception):
    detail: str
    code: str


class MessageNotFound(MessagePermissionError):
    pass


class MessagePermissionDenied(MessagePermissionError):
    pass


def get_message_for_user_or_raise(user, message_uuid):
    try:
        message = (
            Message.objects.select_related("channel__server", "author")
            .prefetch_related("channel__allowed_roles")
            .get(uuid=message_uuid)
        )
    except Message.DoesNotExist as exc:
        raise MessageNotFound(detail="Message not found.", code="not_found") from exc

    user_pk = user.pk

    if message.channel.server.owner_id != user_pk:
        try:
            get_channel_for_user_or_raise(user, message.channel.uuid)
        except ChannelNotFound as exc:
            raise MessageNotFound(detail=exc.detail, code=exc.code) from exc
        except ChannelPermissionDenied as exc:
            raise MessagePermissionDenied(detail=exc.detail, code=exc.code) from exc

    if message.author_id != user_pk and message.channel.server.owner_id != user_pk:
        raise MessagePermissionDenied(detail="Permission denied.", code="permission_denied")

    return message
