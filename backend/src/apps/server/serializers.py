from rest_framework import serializers

from .models.channel import Channel
from .models.server import Server


class ChannelShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Channel
        fields = ["uuid", "name", "channel_type"]


class ServerListSerializer(serializers.ModelSerializer):
    channels = ChannelShortSerializer(many=True, read_only=True)
    is_owner = serializers.SerializerMethodField()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.owner_id == request.user.pk

    class Meta:
        model = Server
        fields = ["uuid", "name", "channels", "is_owner"]


class ChannelCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
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
            "channel_type",
            "topic",
            "is_public",
            "allowed_roles",
            "created_at",
        ]
