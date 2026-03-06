from rest_framework import serializers


class ReceiveMessageSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    content = serializers.CharField(
        max_length=4000,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "blank": "Blank message",
            "max_length": "Message is too long, max 4000 symbols",
        },
    )
