from rest_framework import serializers

from src.apps.chat.models import Message


class MessageReadSerializer(serializers.ModelSerializer):
    author_profile_display_name = serializers.ReadOnlyField(source="author.profile.display_name")

    class Meta:
        model = Message
        fields = [
            "uuid",
            "author",
            "author_profile_display_name",
            "content",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


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


class ChannelReadStateSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    unread_count = serializers.IntegerField(min_value=0)
    last_read_message_uuid = serializers.UUIDField(allow_null=True)


class ChannelMarkReadSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    last_read_message_uuid = serializers.UUIDField(required=False, allow_null=True)
