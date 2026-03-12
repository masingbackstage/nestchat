from rest_framework import serializers

from src.apps.chat.serializers import (
    ReceiveMessageSerializer,
    ToggleReactionSerializer,
    UpdateMessageSerializer,
)
from src.apps.dm.serializers import (
    CreateDMMessageSerializer,
    ToggleDMReactionSerializer,
    UpdateDMMessageSerializer,
)

from .enums import ChatAction, ModuleType


class JoinChannelPayloadSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()


class JoinDMConversationPayloadSerializer(serializers.Serializer):
    conversation_uuid = serializers.UUIDField()


class MessageUuidPayloadSerializer(serializers.Serializer):
    message_uuid = serializers.UUIDField()


class DMMessageUuidPayloadSerializer(serializers.Serializer):
    dm_message_uuid = serializers.UUIDField()


class ToggleReactionPayloadSerializer(serializers.Serializer):
    message_uuid = serializers.UUIDField()
    emoji = serializers.CharField(max_length=16)

    def validate(self, attrs):
        emoji_serializer = ToggleReactionSerializer(data={"emoji": attrs.get("emoji")})
        emoji_serializer.is_valid(raise_exception=True)
        attrs["emoji"] = emoji_serializer.validated_data["emoji"]
        return attrs


class ToggleDMReactionPayloadSerializer(serializers.Serializer):
    dm_message_uuid = serializers.UUIDField()
    emoji = serializers.CharField(max_length=16)

    def validate(self, attrs):
        emoji_serializer = ToggleDMReactionSerializer(data={"emoji": attrs.get("emoji")})
        emoji_serializer.is_valid(raise_exception=True)
        attrs["emoji"] = emoji_serializer.validated_data["emoji"]
        return attrs


class GatewayRequestSerializer(serializers.Serializer):
    module = serializers.ChoiceField(choices=ModuleType.choices)
    action = serializers.CharField()
    payload = serializers.DictField()

    def validate(self, data):
        module = data.get("module")
        action = data.get("action")
        payload = data.get("payload")

        if module == ModuleType.CHAT:
            valid_actions = ChatAction.values
            if action not in valid_actions:
                raise serializers.ValidationError(
                    {"action": f"Invalid action for chat module: {valid_actions}"}
                )

            if action == ChatAction.SEND_MESSAGE:
                payload_serializer = ReceiveMessageSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.JOIN_CHANNEL:
                channel_uuid = payload.get("channel_uuid")
                payload_serializer = JoinChannelPayloadSerializer(
                    data={"channel_uuid": channel_uuid}
                )
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.EDIT_MESSAGE:
                payload_serializer = UpdateMessageSerializer(
                    data={"content": payload.get("content")}
                )
                if payload_serializer.is_valid():
                    message_uuid_serializer = MessageUuidPayloadSerializer(
                        data={"message_uuid": payload.get("message_uuid")}
                    )
                    if message_uuid_serializer.is_valid():
                        data["payload"] = {
                            "message_uuid": message_uuid_serializer.validated_data["message_uuid"],
                            **payload_serializer.validated_data,
                        }
                    else:
                        raise serializers.ValidationError(
                            {"payload": message_uuid_serializer.errors}
                        )
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.DELETE_MESSAGE:
                payload_serializer = MessageUuidPayloadSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.TOGGLE_REACTION:
                payload_serializer = ToggleReactionPayloadSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.JOIN_DM_CONVERSATION:
                payload_serializer = JoinDMConversationPayloadSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.SEND_DM_MESSAGE:
                content_serializer = CreateDMMessageSerializer(
                    data={
                        "content": payload.get("content"),
                        "client_id": payload.get("client_id"),
                    }
                )
                if not content_serializer.is_valid():
                    raise serializers.ValidationError({"payload": content_serializer.errors})
                conversation_serializer = JoinDMConversationPayloadSerializer(
                    data={"conversation_uuid": payload.get("conversation_uuid")}
                )
                if not conversation_serializer.is_valid():
                    raise serializers.ValidationError({"payload": conversation_serializer.errors})
                data["payload"] = {
                    "conversation_uuid": conversation_serializer.validated_data["conversation_uuid"],
                    **content_serializer.validated_data,
                }
            elif action == ChatAction.EDIT_DM_MESSAGE:
                payload_serializer = UpdateDMMessageSerializer(
                    data={"content": payload.get("content")}
                )
                if payload_serializer.is_valid():
                    message_uuid_serializer = DMMessageUuidPayloadSerializer(
                        data={"dm_message_uuid": payload.get("dm_message_uuid")}
                    )
                    if message_uuid_serializer.is_valid():
                        data["payload"] = {
                            "dm_message_uuid": message_uuid_serializer.validated_data[
                                "dm_message_uuid"
                            ],
                            **payload_serializer.validated_data,
                        }
                    else:
                        raise serializers.ValidationError(
                            {"payload": message_uuid_serializer.errors}
                        )
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.DELETE_DM_MESSAGE:
                payload_serializer = DMMessageUuidPayloadSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})
            elif action == ChatAction.TOGGLE_DM_REACTION:
                payload_serializer = ToggleDMReactionPayloadSerializer(data=payload)
                if payload_serializer.is_valid():
                    data["payload"] = payload_serializer.validated_data
                else:
                    raise serializers.ValidationError({"payload": payload_serializer.errors})

        elif module == ModuleType.PRESENCE:
            pass

        return data
