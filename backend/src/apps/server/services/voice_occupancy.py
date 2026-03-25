import re

from django.contrib.auth import get_user_model

from src.apps.server.enums import ChannelType
from src.apps.server.models import Channel, Server, VoiceChannelOccupant

ROOM_NAME_PATTERN = re.compile(
    r"^server:(?P<server_uuid>[0-9a-fA-F-]+):channel:(?P<channel_uuid>[0-9a-fA-F-]+)$"
)

User = get_user_model()


def parse_room_name(room_name: str) -> tuple[str, str] | None:
    match = ROOM_NAME_PATTERN.fullmatch(room_name.strip())
    if not match:
        return None
    return match.group("server_uuid"), match.group("channel_uuid")


def upsert_voice_occupant(server_uuid: str, channel_uuid: str, user_uuid: str) -> list[str]:
    try:
        server = Server.objects.get(uuid=server_uuid)
        channel = Channel.objects.get(uuid=channel_uuid, server=server)
        user = User.objects.get(uuid=user_uuid)
    except (Server.DoesNotExist, Channel.DoesNotExist, User.DoesNotExist):
        return []

    if channel.channel_type != ChannelType.VOICE:
        return []

    existing = (
        VoiceChannelOccupant.objects.select_related("channel")
        .filter(server=server, user=user)
        .first()
    )
    if existing:
        if existing.channel_id == channel.uuid:
            return [str(channel.uuid)]
        previous_channel_uuid = str(existing.channel.uuid)
        existing.channel = channel
        existing.save(update_fields=["channel", "updated_at"])
        return [previous_channel_uuid, str(channel.uuid)]

    VoiceChannelOccupant.objects.create(server=server, channel=channel, user=user)
    return [str(channel.uuid)]


def remove_voice_occupant(server_uuid: str, user_uuid: str) -> list[str]:
    existing = (
        VoiceChannelOccupant.objects.select_related("channel")
        .filter(server__uuid=server_uuid, user__uuid=user_uuid)
        .first()
    )
    if not existing:
        return []

    channel_uuid = str(existing.channel.uuid)
    existing.delete()
    return [channel_uuid]


def clear_voice_channel(server_uuid: str, channel_uuid: str) -> list[str]:
    deleted_count, _ = VoiceChannelOccupant.objects.filter(
        server__uuid=server_uuid,
        channel__uuid=channel_uuid,
    ).delete()
    if not deleted_count:
        return []
    return [channel_uuid]


def list_voice_occupants(channel_uuid: str):
    return (
        VoiceChannelOccupant.objects.filter(channel__uuid=channel_uuid)
        .select_related("user", "user__profile")
        .order_by("created_at", "user_id")
    )
