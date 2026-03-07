import json
import uuid
from datetime import date, datetime

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from src.apps.chat.models import Message, MessageReaction
from src.apps.chat.serializers import MessageReadSerializer
from src.apps.chat.services import (
    ChannelNotFound,
    ChannelPermissionDenied,
    MessageNotFound,
    MessagePermissionDenied,
    get_channel_for_user_or_raise,
    get_message_for_user_or_raise,
)
from src.apps.gateway.enums import ChatAction, ModuleType
from src.apps.gateway.serializers import GatewayRequestSerializer
from src.apps.profile.models import Profile
from src.apps.server.models import Channel, Server


class GatewayConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        await self.accept()

        await self.set_online_status(True)

        self.personal_group = f"user_{self.user.pk}"
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        self.channel_groups = await self.get_user_channel_groups()
        self.joined_channel_groups = set(self.channel_groups)
        for group in self.channel_groups:
            await self.channel_layer.group_add(group, self.channel_name)

        await self.emit_presence_status_changed(True)

    async def disconnect(self, close_code):
        if hasattr(self, "user") and not self.user.is_anonymous:
            await self.set_online_status(False)
            await self.emit_presence_status_changed(False)

            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
            if hasattr(self, "channel_groups"):
                for group in self.channel_groups:
                    await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
        if await self.is_rate_limited("receive", settings.GATEWAY_RECEIVE_RATE_LIMIT_PER_MINUTE):
            await self.gateway_send(
                {
                    "module": "system",
                    "action": "error",
                    "payload": {"code": "rate_limited", "detail": "Too many requests."},
                }
            )
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.gateway_send(
                {
                    "module": "system",
                    "action": "error",
                    "payload": "Wysłano nieprawidłowy format JSON.",
                }
            )
            return

        serializer = GatewayRequestSerializer(data=data)

        if not serializer.is_valid():
            await self.gateway_send(
                {"module": "system", "action": "error", "payload": serializer.errors}
            )
            return

        valid_data = serializer.validated_data
        module = valid_data["module"]
        action = valid_data["action"]
        payload = valid_data["payload"]

        if module == ModuleType.CHAT:
            await self.handle_chat_module(action, payload)
        elif module == ModuleType.PRESENCE:
            pass

    async def handle_chat_module(self, action, payload):
        if action == ChatAction.JOIN_CHANNEL:
            channel_uuid = payload["channel_uuid"]
            try:
                await self.get_allowed_channel(channel_uuid)
            except ChannelNotFound as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return
            except ChannelPermissionDenied as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return

            group_name = f"channel_{channel_uuid}"
            if group_name not in self.joined_channel_groups:
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.joined_channel_groups.add(group_name)
            await self.gateway_send(
                {
                    "module": "system",
                    "action": "ack",
                    "payload": {
                        "action": "join_channel",
                        "channel_uuid": str(channel_uuid),
                    },
                }
            )
            return

        if action == ChatAction.SEND_MESSAGE:
            if await self.is_rate_limited(
                "send_message", settings.GATEWAY_SEND_MESSAGE_RATE_LIMIT_PER_MINUTE
            ):
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": "rate_limited", "detail": "Too many requests."},
                    }
                )
                return

            channel_uuid = payload["channel_uuid"]
            content = payload["content"]
            client_id = payload.get("client_id")

            try:
                channel = await self.get_allowed_channel(channel_uuid)
            except ChannelNotFound as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return
            except ChannelPermissionDenied as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return

            message = await self.save_message(channel, content)
            author_name = await self.get_author_name()

            group_name = f"channel_{channel_uuid}"
            if group_name not in self.joined_channel_groups:
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.joined_channel_groups.add(group_name)
            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "gateway_send_event",
                    "module": ModuleType.CHAT.value,
                    "action": "new_message",
                    "payload": {
                        "id": str(message.uuid),
                        "channel_id": str(channel_uuid),
                        "content": content,
                        "author": author_name,
                        "author_uuid": str(self.user.uuid),
                        "client_id": client_id,
                    },
                },
            )
            return

        if action == ChatAction.EDIT_MESSAGE:
            message_uuid = payload["message_uuid"]
            content = payload["content"]

            try:
                message = await self.get_allowed_message(message_uuid)
            except MessageNotFound as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return
            except MessagePermissionDenied as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return

            if message.is_deleted:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {
                            "code": "invalid_operation",
                            "detail": "Cannot edit deleted message.",
                        },
                    }
                )
                return

            message = await self.update_message_content(message.uuid, content)
            payload_data = await self.serialize_message(message.uuid)
            group_name = f"channel_{payload_data['channel_uuid']}"
            if group_name not in self.joined_channel_groups:
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.joined_channel_groups.add(group_name)

            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "gateway_send_event",
                    "module": ModuleType.CHAT.value,
                    "action": "message_updated",
                    "payload": payload_data,
                },
            )
            return

        if action == ChatAction.DELETE_MESSAGE:
            message_uuid = payload["message_uuid"]
            try:
                message = await self.get_allowed_message(message_uuid)
            except MessageNotFound as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return
            except MessagePermissionDenied as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return

            message = await self.soft_delete_message(message.uuid)
            payload_data = await self.serialize_message(message.uuid)
            group_name = f"channel_{payload_data['channel_uuid']}"
            if group_name not in self.joined_channel_groups:
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.joined_channel_groups.add(group_name)

            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "gateway_send_event",
                    "module": ModuleType.CHAT.value,
                    "action": "message_deleted",
                    "payload": payload_data,
                },
            )
            return

        if action == ChatAction.TOGGLE_REACTION:
            message_uuid = payload["message_uuid"]
            emoji = payload["emoji"]

            try:
                message = await self.get_allowed_message(message_uuid)
            except MessageNotFound as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return
            except MessagePermissionDenied as exc:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {"code": exc.code, "detail": exc.detail},
                    }
                )
                return

            if message.is_deleted:
                await self.gateway_send(
                    {
                        "module": "system",
                        "action": "error",
                        "payload": {
                            "code": "validation_error",
                            "detail": "Cannot react to deleted message.",
                        },
                    }
                )
                return

            message = await self.toggle_message_reaction(message.uuid, emoji)
            payload_data = await self.serialize_message(message.uuid)
            group_name = f"channel_{payload_data['channel_uuid']}"
            if group_name not in self.joined_channel_groups:
                await self.channel_layer.group_add(group_name, self.channel_name)
                self.joined_channel_groups.add(group_name)

            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "gateway_send_event",
                    "module": ModuleType.CHAT.value,
                    "action": "message_reactions_updated",
                    "payload": payload_data,
                },
            )

    async def gateway_send_event(self, event):
        await self.gateway_send(
            {"module": event["module"], "action": event["action"], "payload": event["payload"]}
        )

    async def gateway_send(self, data_dict):
        await self.send(text_data=json.dumps(data_dict))

    async def emit_presence_status_changed(self, is_online):
        targets = await self.get_presence_targets()
        timestamp = timezone.now().isoformat()
        for target in targets:
            status_payload = {
                "server_uuid": target["server_uuid"],
                "member_uuid": str(self.user.uuid),
                "is_online": is_online,
                "timestamp": timestamp,
            }
            members_changed_payload = {
                "server_uuid": target["server_uuid"],
                "reason": "presence_changed",
                "timestamp": timestamp,
            }
            for group_name in target["recipient_group_names"]:
                await self.channel_layer.group_send(
                    group_name,
                    {
                        "type": "gateway_send_event",
                        "module": ModuleType.PRESENCE.value,
                        "action": "status_changed",
                        "payload": status_payload,
                    },
                )
                await self.channel_layer.group_send(
                    group_name,
                    {
                        "type": "gateway_send_event",
                        "module": ModuleType.PRESENCE.value,
                        "action": "members_changed",
                        "payload": members_changed_payload,
                    },
                )

    @database_sync_to_async
    def set_online_status(self, is_online):
        Profile.objects.filter(user=self.user).update(is_online=is_online)

    @database_sync_to_async
    def get_user_channel_groups(self):
        servers = Server.objects.filter(members=self.user) | Server.objects.filter(owner=self.user)
        channels = Channel.objects.filter(server__in=servers.distinct())
        return [f"channel_{channel.uuid}" for channel in channels]

    @database_sync_to_async
    def get_presence_targets(self):
        servers = (
            Server.objects.filter(members=self.user) | Server.objects.filter(owner=self.user)
        ).distinct()
        targets = []
        for server in servers.prefetch_related("members"):
            member_pks = set(server.members.values_list("pk", flat=True))
            member_pks.add(server.owner_id)
            if not member_pks:
                continue
            targets.append(
                {
                    "server_uuid": str(server.uuid),
                    "recipient_group_names": [f"user_{member_pk}" for member_pk in member_pks],
                }
            )
        return targets

    @database_sync_to_async
    def get_allowed_channel(self, channel_uuid):
        return get_channel_for_user_or_raise(self.user, channel_uuid)

    @database_sync_to_async
    def save_message(self, channel, content):
        return Message.objects.create(channel=channel, author=self.user, content=content)

    @database_sync_to_async
    def get_allowed_message(self, message_uuid):
        return get_message_for_user_or_raise(self.user, message_uuid)

    @database_sync_to_async
    def update_message_content(self, message_uuid, content):
        message = Message.objects.get(uuid=message_uuid)
        message.content = content
        message.edited_at = timezone.now()
        message.save(update_fields=["content", "edited_at", "updated_at"])
        return message

    @database_sync_to_async
    def soft_delete_message(self, message_uuid):
        message = Message.objects.get(uuid=message_uuid)
        if not message.is_deleted:
            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.deleted_by = self.user
            message.content = ""
            message.save(
                update_fields=["is_deleted", "deleted_at", "deleted_by", "content", "updated_at"]
            )
        return message

    @database_sync_to_async
    def toggle_message_reaction(self, message_uuid, emoji):
        message = Message.objects.get(uuid=message_uuid)
        reaction = MessageReaction.objects.filter(
            message=message, user=self.user, emoji=emoji
        ).first()
        if reaction:
            reaction.delete()
        else:
            MessageReaction.objects.create(message=message, user=self.user, emoji=emoji)
        return message

    @database_sync_to_async
    def serialize_message(self, message_uuid):
        message = (
            Message.objects.select_related("author", "author__profile", "channel")
            .prefetch_related("reactions")
            .get(uuid=message_uuid)
        )
        data = MessageReadSerializer(message, context={"user": self.user}).data
        for key, value in list(data.items()):
            if isinstance(value, uuid.UUID):
                data[key] = str(value)
            elif isinstance(value, (datetime, date)):
                data[key] = value.isoformat()
        return data

    @database_sync_to_async
    def get_author_name(self):
        if hasattr(self.user, "profile") and self.user.profile.display_name:
            return self.user.profile.display_name
        return self.user.email

    @database_sync_to_async
    def is_rate_limited(self, bucket, limit):
        cache_key = f"gateway:ratelimit:{bucket}:user:{self.user.pk}"
        timeout = settings.GATEWAY_RATE_LIMIT_WINDOW_SECONDS
        if cache.add(cache_key, 1, timeout=timeout):
            return False

        try:
            current = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, timeout=timeout)
            return False

        return current > limit
