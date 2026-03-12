from rest_framework import serializers

from src.apps.chat.models import Message


class MessageReactionSummarySerializer(serializers.Serializer):
    emoji = serializers.CharField()
    count = serializers.IntegerField(min_value=1)
    reacted_by_me = serializers.BooleanField()


class MessageReadSerializer(serializers.ModelSerializer):
    author_profile_display_name = serializers.ReadOnlyField(source="author.profile.display_name")
    avatar_url = serializers.SerializerMethodField()
    channel_uuid = serializers.ReadOnlyField(source="channel.uuid")
    is_edited = serializers.SerializerMethodField()
    edited_at = serializers.DateTimeField(read_only=True, allow_null=True)
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "uuid",
            "channel_uuid",
            "author",
            "author_profile_display_name",
            "avatar_url",
            "content",
            "is_deleted",
            "is_edited",
            "edited_at",
            "reactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def get_avatar_url(self, obj):
        profile = getattr(obj.author, "profile", None)
        avatar = getattr(profile, "avatar", None)
        if not avatar:
            return None

        try:
            avatar_url = avatar.url
        except Exception:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(avatar_url)
        return avatar_url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = ""
        return data

    def get_reactions(self, obj):
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        user_id = getattr(user, "pk", None)
        reactions = list(obj.reactions.all())
        if not reactions:
            return []

        grouped: dict[str, dict[str, object]] = {}
        for reaction in reactions:
            bucket = grouped.setdefault(
                reaction.emoji,
                {"emoji": reaction.emoji, "count": 0, "reacted_by_me": False},
            )
            bucket["count"] = int(bucket["count"]) + 1
            if user_id and reaction.user_id == user_id:
                bucket["reacted_by_me"] = True

        sorted_items = [grouped[key] for key in sorted(grouped.keys())]
        return MessageReactionSummarySerializer(sorted_items, many=True).data


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


class ToggleReactionSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=16)

    def validate_emoji(self, value):
        emoji = value.strip()
        if not emoji:
            raise serializers.ValidationError("Emoji is required.")
        return emoji


class ChannelReadStateSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    unread_count = serializers.IntegerField(min_value=0)
    last_read_message_uuid = serializers.UUIDField(allow_null=True)


class ChannelMarkReadSerializer(serializers.Serializer):
    channel_uuid = serializers.UUIDField()
    last_read_message_uuid = serializers.UUIDField(required=False, allow_null=True)
