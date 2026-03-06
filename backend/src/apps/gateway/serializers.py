from rest_framework import serializers

from src.apps.chat.serializers import ReceiveMessageSerializer

from .enums import ChatAction, ModuleType


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

        elif module == ModuleType.PRESENCE:
            pass

        return data
