from dataclasses import dataclass

from src.apps.server.models import Channel, ServerMember


@dataclass(slots=True)
class ChannelPermissionError(Exception):
    detail: str
    code: str


class ChannelNotFound(ChannelPermissionError):
    pass


class ChannelPermissionDenied(ChannelPermissionError):
    pass


def get_channel_for_user_or_raise(user, channel_uuid):
    try:
        channel = (
            Channel.objects.prefetch_related("allowed_roles")
            .select_related("server")
            .get(uuid=channel_uuid)
        )
    except Channel.DoesNotExist as exc:
        raise ChannelNotFound(detail="Channel not found.", code="not_found") from exc

    try:
        server_member = (
            ServerMember.objects.prefetch_related("roles")
            .get(server=channel.server, user=user)
        )
    except ServerMember.DoesNotExist as exc:
        raise ChannelPermissionDenied(
            detail="Permission denied.",
            code="permission_denied",
        ) from exc

    if not channel.is_public:
        user_roles = set(server_member.roles.all())
        channel_roles = set(channel.allowed_roles.all())
        if not user_roles.intersection(channel_roles):
            raise ChannelPermissionDenied(
                detail="Permission denied.",
                code="permission_denied",
            )

    return channel
