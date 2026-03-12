from django.contrib.auth import get_user_model
from rest_framework import serializers

from src.apps.dm.constants import ALLOWED_DM_REACTION_EMOJIS
from src.apps.dm.models import DMConversation, DMMessage

User = get_user_model()


class DMMessageReactionSummarySerializer(serializers.Serializer):
    emoji = serializers.CharField()
    count = serializers.IntegerField(min_value=1)
    reacted_by_me = serializers.BooleanField()


class DMMessageReadSerializer(serializers.ModelSerializer):
    conversation_uuid = serializers.ReadOnlyField(source="conversation.uuid")
    author_profile_display_name = serializers.ReadOnlyField(source="author.profile.display_name")
    avatar_url = serializers.SerializerMethodField()
    is_edited = serializers.SerializerMethodField()
    edited_at = serializers.DateTimeField(read_only=True, allow_null=True)
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = DMMessage
        fields = [
            "uuid",
            "conversation_uuid",
            "author",
            "author_profile_display_name",
            "avatar_url",
            "content",
            "is_deleted",
            "is_edited",
            "edited_at",
            "reactions",
            "ciphertext",
            "nonce",
            "encryption_version",
            "sender_key_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

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

    def get_is_edited(self, obj):
        return obj.edited_at is not None

    def get_reactions(self, obj):
        user = self.context.get("user") or getattr(self.context.get("request"), "user", None)
        user_id = getattr(user, "pk", None)
        reactions = list(obj.reactions.all())
        if not reactions:
            return []

        grouped = {}
        for reaction in reactions:
            bucket = grouped.setdefault(
                reaction.emoji,
                {"emoji": reaction.emoji, "count": 0, "reacted_by_me": False},
            )
            bucket["count"] = int(bucket["count"]) + 1
            if user_id and reaction.user_id == user_id:
                bucket["reacted_by_me"] = True

        sorted_items = [grouped[key] for key in sorted(grouped.keys())]
        return DMMessageReactionSummarySerializer(sorted_items, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data["content"] = ""
        return data


class DMConversationParticipantSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(source="user.uuid")
    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    def get_display_name(self, obj):
        profile = getattr(obj.user, "profile", None)
        if profile and profile.display_name:
            return profile.display_name
        return obj.user.email.split("@")[0]

    def get_avatar_url(self, obj):
        profile = getattr(obj.user, "profile", None)
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

    def get_is_online(self, obj):
        profile = getattr(obj.user, "profile", None)
        return bool(getattr(profile, "is_online", False))


class DMConversationListItemSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = DMConversation
        fields = [
            "uuid",
            "conversation_type",
            "title",
            "avatar_url",
            "participants",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        try:
            avatar_url = obj.avatar.url
        except Exception:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(avatar_url)
        return avatar_url

    def get_participants(self, obj):
        participants = obj.conversation_participants.select_related("user", "user__profile").all()
        return DMConversationParticipantSerializer(
            participants,
            many=True,
            context=self.context,
        ).data

    def get_last_message(self, obj):
        last_message = getattr(obj, "_prefetched_last_message", None)
        if last_message is None:
            last_message = (
                obj.messages.select_related("author", "author__profile")
                .prefetch_related("reactions")
                .order_by("-created_at", "-uuid")
                .first()
            )
        if not last_message:
            return None
        return DMMessageReadSerializer(last_message, context=self.context).data


class CreateDMConversationSerializer(serializers.Serializer):
    participant_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    title = serializers.CharField(max_length=120, required=False, allow_blank=True, allow_null=True)

    def validate_participant_uuids(self, value):
        unique = []
        seen = set()
        for item in value:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique


class CreateDirectDMConversationSerializer(serializers.Serializer):
    user_uuid = serializers.UUIDField()


class CreateDMMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=4000,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "blank": "Blank message",
            "max_length": "Message is too long, max 4000 symbols",
        },
    )
    client_id = serializers.CharField(max_length=64, required=False)


class UpdateDMMessageSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=4000,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "blank": "Blank message",
            "max_length": "Message is too long, max 4000 symbols",
        },
    )


class ToggleDMReactionSerializer(serializers.Serializer):
    emoji = serializers.CharField(max_length=16)

    def validate_emoji(self, value):
        emoji = value.strip()
        if not emoji:
            raise serializers.ValidationError("Emoji is required.")
        if emoji not in ALLOWED_DM_REACTION_EMOJIS:
            raise serializers.ValidationError("This emoji is not allowed.")
        return emoji


class MarkDMConversationReadSerializer(serializers.Serializer):
    last_read_message_uuid = serializers.UUIDField(required=False, allow_null=True)
