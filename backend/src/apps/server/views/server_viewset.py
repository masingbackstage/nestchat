from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.apps.server.models import Channel, Role, Server, ServerEmoji
from src.apps.server.serializers import (
    ChannelCreateSerializer,
    ChannelDetailSerializer,
    ServerEmojiCreateSerializer,
    ServerEmojiSerializer,
    ServerListSerializer,
    ServerMembersResponseSerializer,
)


class ServerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServerListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        return (
            Server.objects.filter(models.Q(owner=user) | models.Q(members=user))
            .distinct()
            .prefetch_related("channels", "emojis")
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

        response_serializer = ChannelDetailSerializer(channel)
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

        def get_profile(user):
            try:
                return user.profile
            except Exception:
                return None

        def to_display_name(user):
            profile = get_profile(user)
            if profile and profile.display_name:
                return profile.display_name
            return user.email.split("@")[0]

        def to_avatar_url(user):
            profile = get_profile(user)
            if profile and profile.avatar:
                return request.build_absolute_uri(profile.avatar.url)
            return None

        def to_custom_status(user):
            profile = get_profile(user)
            if profile and profile.custom_status:
                return profile.custom_status
            return None

        def to_is_online(user):
            profile = get_profile(user)
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
                "display_name": to_display_name(user),
                "is_online": to_is_online(user),
                "roles": [{"uuid": role.uuid, "name": role.name} for role in roles],
                "avatar_url": to_avatar_url(user),
                "custom_status": to_custom_status(user),
            }

        owner = server.owner
        if owner.pk not in members_by_user_id:
            members_by_user_id[owner.pk] = {
                "uuid": owner.uuid,
                "display_name": to_display_name(owner),
                "is_online": to_is_online(owner),
                "roles": [],
                "avatar_url": to_avatar_url(owner),
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
