from rest_framework import serializers

from src.apps.chat.models import Message


class MessageReadSerializer(serializers.ModelSerializer):
    author_profile_display_name = serializers.ReadOnlyField(source='author.profile.display_name')

    class Meta:
        model = Message
        fields = [
            'uuid',
            'author',
            'author_profile_display_name',
            'content',
            'created_at',
            'updated_at'
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
