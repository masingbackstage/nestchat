from rest_framework import serializers

from .models.channel import Channel
from .models.server_emoji import ServerEmoji
from .models.server import Server


class ChannelShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Channel
        fields = ["uuid", "name", "channel_emoji", "channel_type"]


class ServerListSerializer(serializers.ModelSerializer):
    channels = ChannelShortSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.pk

    def get_avatar_url(self, obj):
        avatar = getattr(obj, "avatar", None)
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

    class Meta:
        model = Server
        fields = ["uuid", "name", "avatar_url", "channels", "is_owner"]


class ChannelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    channel_emoji = serializers.CharField(max_length=16, required=False, allow_blank=True)
    channel_type = serializers.ChoiceField(choices=Channel._meta.get_field("channel_type").choices)
    topic = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    is_public = serializers.BooleanField()
    allowed_roles = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )

    def validate_allowed_roles(self, value):
        if not value:
            return []
        unique = []
        seen = set()
        for item in value:
            if item in seen:
                continue
            seen.add(item)
            unique.append(item)
        return unique


class ChannelDetailSerializer(serializers.ModelSerializer):
    allowed_roles = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Channel
        fields = [
            "uuid",
            "name",
            "channel_emoji",
            "channel_type",
            "topic",
            "is_public",
            "allowed_roles",
            "created_at",
        ]


class ServerEmojiSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()

    class Meta:
        model = ServerEmoji
        fields = ["uuid", "name", "token", "image_url", "is_animated", "created_at"]

    def get_image_url(self, obj):
        if not obj.image:
            return None

        try:
            image_url = obj.image.url
        except Exception:
            return None

        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(image_url)
        return image_url

    def get_token(self, obj):
        return f":{obj.name}:"


class ServerEmojiCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerEmoji
        fields = ["name", "image", "is_animated"]


class MemberRoleSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    name = serializers.CharField()


class ServerMemberItemSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    display_name = serializers.CharField()
    is_online = serializers.BooleanField()
    roles = MemberRoleSerializer(many=True)
    avatar_url = serializers.CharField(allow_null=True, required=False)
    custom_status = serializers.CharField(allow_null=True, required=False)


class ServerMembersGroupSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    members = ServerMemberItemSerializer(many=True)


class ServerMembersResponseSerializer(serializers.Serializer):
    groups = ServerMembersGroupSerializer(many=True)
