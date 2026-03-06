import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from src.apps.chat.models import Message
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

        self.personal_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.personal_group, self.channel_name)

        self.channel_groups = await self.get_user_channel_groups()
        for group in self.channel_groups:
            await self.channel_layer.group_add(group, self.channel_name)

    async def disconnect(self, close_code):
        if hasattr(self, "user") and not self.user.is_anonymous:
            await self.set_online_status(False)

            await self.channel_layer.group_discard(self.personal_group, self.channel_name)
            if hasattr(self, "channel_groups"):
                for group in self.channel_groups:
                    await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
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
        if action == ChatAction.SEND_MESSAGE:
            channel_uuid = payload["channel_uuid"]
            content = payload["content"]

            message = await self.save_message(channel_uuid, content)
            author_name = await self.get_author_name()

            group_name = f"channel_{channel_uuid}"
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
                    },
                },
            )

    async def gateway_send_event(self, event):
        await self.gateway_send(
            {"module": event["module"], "action": event["action"], "payload": event["payload"]}
        )

    async def gateway_send(self, data_dict):
        await self.send(text_data=json.dumps(data_dict))

    @database_sync_to_async
    def set_online_status(self, is_online):
        Profile.objects.filter(user=self.user).update(is_online=is_online)

    @database_sync_to_async
    def get_user_channel_groups(self):
        servers = Server.objects.filter(members=self.user) | Server.objects.filter(owner=self.user)
        channels = Channel.objects.filter(server__in=servers.distinct())
        return [f"channel_{channel.uuid}" for channel in channels]

    @database_sync_to_async
    def save_message(self, channel_uuid, content):
        channel = Channel.objects.get(uuid=channel_uuid)
        return Message.objects.create(channel=channel, author=self.user, content=content)

    @database_sync_to_async
    def get_author_name(self):
        if hasattr(self.user, "profile") and self.user.profile.display_name:
            return self.user.profile.display_name
        return self.user.email
