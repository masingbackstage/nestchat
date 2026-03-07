from rest_framework import serializers

from src.apps.chat.models import Message


class MessageReadSerializer(serializers.ModelSerializer):
    author_profile_display_name = serializers.ReadOnlyField(source="author.profile.display_name")
    channel_uuid = serializers.ReadOnlyField(source="channel.uuid")
    is_edited = serializers.SerializerMethodField()
    edited_at = serializers.DateTimeField(read_only=True, allow_null=True)

    class Meta:
        model = Message
        fields = [
            "uuid",
            "channel_uuid",
            "author",
            "author_profile_display_name",
            "content",
            "is_deleted",
            "is_edited",
            "edited_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = ""
        return data


class ReceiveMessageSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    client_id = serializers.CharField(max_length=64, required=False)
    content = serializers.CharField(
        max_length=4000,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "blank": "Blank message",
            "max_length": "Message is too long, max 4000 symbols",
        },
    )


class UpdateMessageSerializer(serializers.Serializer):
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
