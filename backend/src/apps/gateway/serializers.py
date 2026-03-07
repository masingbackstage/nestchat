from rest_framework import serializers

from src.apps.chat.serializers import (
    ReceiveMessageSerializer,
    ToggleReactionSerializer,
    UpdateMessageSerializer,
)

from .enums import ChatAction, ModuleType


class JoinChannelPayloadSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()


class MessageUuidPayloadSerializer(serializers.Serializer):
    message_uuid = serializers.UUIDField()


class ToggleReactionPayloadSerializer(serializers.Serializer):
    message_uuid = serializers.UUIDField()
    emoji = serializers.CharField(max_length=16)

    def validate(self, attrs):
        emoji_serializer = ToggleReactionSerializer(data={"emoji": attrs.get("emoji")})
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

        elif module == ModuleType.PRESENCE:
            pass

        return data
