from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from livekit import api
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from src.apps.gateway.enums import ModuleType
from src.apps.server.enums import ChannelType
from src.apps.server.models import Channel, Role, Server, ServerEmoji
from src.apps.server.serializers import (
    ChannelCreateSerializer,
    ChannelDetailSerializer,
    ServerEmojiCreateSerializer,
    ServerEmojiSerializer,
    ServerListSerializer,
    ServerMembersResponseSerializer,
    VoiceTokenRequestSerializer,
    VoiceTokenResponseSerializer,
    build_user_avatar_url,
    build_user_display_name,
    build_voice_occupant_payload,
)
from src.apps.server.services.voice_occupancy import (
    clear_voice_channel,
    list_voice_occupants,
    parse_room_name,
    remove_voice_occupant,
    upsert_voice_occupant,
)


def emit_voice_members_changed(server: Server, channel_uuid: str) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    occupants = [
        build_voice_occupant_payload(item.user) for item in list_voice_occupants(channel_uuid)
    ]
    payload = {
        "server_uuid": str(server.uuid),
        "channel_uuid": channel_uuid,
        "occupants": occupants,
        "timestamp": timezone.now().isoformat(),
    }
    member_pks = set(server.members.values_list("pk", flat=True))
    member_pks.add(server.owner_id)
    for member_pk in member_pks:
        async_to_sync(channel_layer.group_send)(
            f"user_{member_pk}",
            {
                "type": "gateway_send_event",
                "module": ModuleType.VOICE.value,
                "action": "members_changed",
                "payload": payload,
            },
        )


class LiveKitWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not settings.LIVEKIT_API_KEY or not (
            settings.LIVEKIT_WEBHOOK_SECRET or settings.LIVEKIT_API_SECRET
        ):
            raise APIException("Voice webhook is not configured.")

        auth_header = request.headers.get("Authorization", "").strip()
        if not auth_header:
            return Response(
                {"detail": "Missing Authorization header."},
                status=status.HTTP_403_FORBIDDEN,
            )

        body = request.body.decode("utf-8")
        auth_token = auth_header.removeprefix("Bearer ").strip()
        verifier = api.TokenVerifier(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_WEBHOOK_SECRET or settings.LIVEKIT_API_SECRET,
        )
        receiver = api.WebhookReceiver(verifier)

        try:
            event = receiver.receive(body, auth_token)
        except Exception:
            return Response(
                {"detail": "Invalid webhook signature."}, status=status.HTTP_403_FORBIDDEN
            )

        room_name = event.room.name if event.room else ""
        room_identifiers = parse_room_name(room_name)
        if not room_identifiers:
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        server_uuid, channel_uuid = room_identifiers
        try:
            server = Server.objects.get(uuid=server_uuid)
        except Server.DoesNotExist:
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        event_name = str(event.event or "").lower()
        participant_identity = event.participant.identity if event.participant else ""

        if event_name == "participant_joined" and participant_identity:
            affected_channel_uuids = upsert_voice_occupant(
                server_uuid, channel_uuid, participant_identity
            )
        elif (
            event_name in {"participant_left", "participant_disconnected"} and participant_identity
        ):
            affected_channel_uuids = remove_voice_occupant(server_uuid, participant_identity)
        elif event_name == "room_finished":
            affected_channel_uuids = clear_voice_channel(server_uuid, channel_uuid)
        else:
            affected_channel_uuids = []

        for affected_channel_uuid in dict.fromkeys(affected_channel_uuids):
            emit_voice_members_changed(server, affected_channel_uuid)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ServerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServerListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        return (
            Server.objects.filter(models.Q(owner=user) | models.Q(members=user))
            .distinct()
            .prefetch_related("channels", "channels__voice_occupants__user__profile", "emojis")
        )

    def has_server_access(self, user, server: Server) -> bool:
        if server.owner_id == user.pk:
            return True
        return server.server_members.filter(user=user).exists()

    @action(detail=True, methods=["post"], url_path="channels")
    def channels(self, request, uuid=None):
        server = get_object_or_404(Server, uuid=uuid)
        if server.owner_id != request.user.pk:
            raise PermissionDenied("Only server owner can create channels.")

        serializer = ChannelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        allowed_role_uuids = validated_data.pop("allowed_roles", [])
        channel_emoji = validated_data.get("channel_emoji")
        validated_data["channel_emoji"] = channel_emoji.strip() if channel_emoji else None
        is_public = validated_data["is_public"]
        if is_public:
            allowed_role_uuids = []

        roles = list(Role.objects.filter(server=server, uuid__in=allowed_role_uuids))
        if len(roles) != len(allowed_role_uuids):
            raise ValidationError({"allowed_roles": "All roles must belong to this server."})

        channel = Channel.objects.create(server=server, **validated_data)
        if roles:
            channel.allowed_roles.set(roles)

        response_serializer = ChannelDetailSerializer(channel, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="emojis")
    def emojis(self, request, uuid=None):
        server = get_object_or_404(Server, uuid=uuid)
        if not self.has_server_access(request.user, server):
            raise PermissionDenied("You do not have access to this server.")

        if request.method.lower() == "get":
            queryset = ServerEmoji.objects.filter(server=server).order_by("name")
            serializer = ServerEmojiSerializer(
                queryset,
                many=True,
                context={"request": request},
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        if server.owner_id != request.user.pk:
            raise PermissionDenied("Only server owner can create emojis.")

        serializer = ServerEmojiCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emoji = serializer.save(server=server)
        response_serializer = ServerEmojiSerializer(emoji, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, uuid=None):
        server = get_object_or_404(
            Server.objects.select_related("owner", "owner__profile"),
            uuid=uuid,
        )
        if not self.has_server_access(request.user, server):
            raise PermissionDenied("You do not have access to this server.")

        server_members = list(
            server.server_members.select_related("user", "user__profile").prefetch_related("roles")
        )

        members_by_user_id: dict[int, dict] = {}

        def to_custom_status(user):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if profile and profile.custom_status:
                return profile.custom_status
            return None

        def to_is_online(user):
            try:
                profile = user.profile
            except Exception:
                profile = None
            if profile:
                return bool(profile.is_online)
            return False

        for server_member in server_members:
            user = server_member.user
            roles = sorted(
                server_member.roles.all(),
                key=lambda role: (role.name.lower(), str(role.uuid)),
            )
            members_by_user_id[user.pk] = {
                "uuid": user.uuid,
                "display_name": build_user_display_name(user),
                "is_online": to_is_online(user),
                "roles": [{"uuid": role.uuid, "name": role.name} for role in roles],
                "avatar_url": build_user_avatar_url(user, request),
                "custom_status": to_custom_status(user),
            }

        owner = server.owner
        if owner.pk not in members_by_user_id:
            members_by_user_id[owner.pk] = {
                "uuid": owner.uuid,
                "display_name": build_user_display_name(owner),
                "is_online": to_is_online(owner),
                "roles": [],
                "avatar_url": build_user_avatar_url(owner, request),
                "custom_status": to_custom_status(owner),
            }

        grouped = {
            "online_with_roles": {
                "key": "online_with_roles",
                "label": "Online — roles",
                "members": [],
            },
            "online": {
                "key": "online",
                "label": "Online",
                "members": [],
            },
            "offline": {
                "key": "offline",
                "label": "Offline",
                "members": [],
            },
        }

        for member in members_by_user_id.values():
            if member["is_online"] and member["roles"]:
                grouped["online_with_roles"]["members"].append(member)
            elif member["is_online"]:
                grouped["online"]["members"].append(member)
            else:
                grouped["offline"]["members"].append(member)

        groups = []
        for group_key in ("online_with_roles", "online", "offline"):
            group = grouped[group_key]
            if not group["members"]:
                continue
            group["members"] = sorted(
                group["members"],
                key=lambda member: (member["display_name"].lower(), str(member["uuid"])),
            )
            groups.append(group)

        response_serializer = ServerMembersResponseSerializer({"groups": groups})
        return Response(response_serializer.data)

    @action(detail=True, methods=["post"], url_path="voice-token")
    def voice_token(self, request, uuid=None):
        server = get_object_or_404(Server, uuid=uuid)
        if not self.has_server_access(request.user, server):
            raise PermissionDenied("You do not have access to this server.")

        req = VoiceTokenRequestSerializer(data=request.data)
        req.is_valid(raise_exception=True)
        channel_uuid = req.validated_data["channel_uuid"]

        channel = get_object_or_404(
            Channel.objects.prefetch_related("allowed_roles"),
            uuid=channel_uuid,
            server=server,
        )

        if channel.channel_type != ChannelType.VOICE:
            raise ValidationError({"channel_uuid": "Channel is not a voice channel."})

        if not channel.is_public and server.owner_id != request.user.pk:
            member = (
                server.server_members.filter(user=request.user).prefetch_related("roles").first()
            )
            if not member:
                raise PermissionDenied("You do not have access to this voice channel.")

            member_role_ids = set(member.roles.values_list("uuid", flat=True))
            allowed_role_ids = set(channel.allowed_roles.values_list("uuid", flat=True))
            if allowed_role_ids and member_role_ids.isdisjoint(allowed_role_ids):
                raise PermissionDenied("You do not have access to this voice channel.")

        if (
            not settings.LIVEKIT_URL
            or not settings.LIVEKIT_API_KEY
            or not settings.LIVEKIT_API_SECRET
        ):
            raise APIException("Voice service is not configured.")

        room_name = f"server:{server.uuid}:channel:{channel.uuid}"
        identity = str(request.user.uuid)

        grants = api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
        )

        token = (
            api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            .with_identity(identity)
            .with_name(identity)
            .with_ttl(timedelta(seconds=settings.LIVEKIT_TOKEN_TTL_SECONDS))
            .with_grants(grants)
            .to_jwt()
        )

        payload = {
            "token": token,
            "livekit_public_url": settings.LIVEKIT_PUBLIC_URL,
            "room_name": room_name,
            "identity": identity,
            "expires_in": settings.LIVEKIT_TOKEN_TTL_SECONDS,
        }
        return Response(VoiceTokenResponseSerializer(payload).data, status=status.HTTP_200_OK)
