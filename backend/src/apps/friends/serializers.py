from rest_framework import serializers

from src.apps.friends.models import Friendship


class FriendUserSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    email = serializers.EmailField()
    display_name = serializers.CharField()
    tag = serializers.CharField(allow_blank=True)
    avatar_url = serializers.CharField(allow_null=True)
    is_online = serializers.BooleanField()
    custom_status = serializers.CharField(allow_blank=True)


class FriendshipSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ["uuid", "status", "created_at", "updated_at", "responded_at", "user"]

    def get_user(self, obj):
        request = self.context["request"]
        counterpart = obj.counterpart_for(request.user)
        profile = getattr(counterpart, "profile", None)
        avatar_url = None
        avatar = getattr(profile, "avatar", None)
        if avatar:
            try:
                avatar_url = avatar.url
            except Exception:
                avatar_url = None
        if request and avatar_url:
            avatar_url = request.build_absolute_uri(avatar_url)

        display_name = (
            getattr(profile, "display_name", "")
            if getattr(profile, "display_name", "")
            else counterpart.email.split("@")[0]
        )
        tag = getattr(profile, "tag", "") if profile else ""
        is_online = bool(getattr(profile, "is_online", False)) if profile else False
        custom_status = getattr(profile, "custom_status", "") if profile else ""

        return {
            "uuid": counterpart.uuid,
            "email": counterpart.email,
            "display_name": display_name,
            "tag": tag,
            "avatar_url": avatar_url,
            "is_online": is_online,
            "custom_status": custom_status,
        }


class FriendshipRequestIncomingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ["uuid", "status", "created_at", "updated_at", "responded_at", "user"]

    def get_user(self, obj):
        request = self.context["request"]
        user = obj.requester
        profile = getattr(user, "profile", None)
        avatar_url = None
        avatar = getattr(profile, "avatar", None)
        if avatar:
            try:
                avatar_url = avatar.url
            except Exception:
                avatar_url = None
        if request and avatar_url:
            avatar_url = request.build_absolute_uri(avatar_url)

        return {
            "uuid": user.uuid,
            "email": user.email,
            "display_name": getattr(profile, "display_name", "") or user.email.split("@")[0],
            "tag": getattr(profile, "tag", "") if profile else "",
            "avatar_url": avatar_url,
            "is_online": bool(getattr(profile, "is_online", False)) if profile else False,
            "custom_status": getattr(profile, "custom_status", "") if profile else "",
        }


class FriendshipRequestOutgoingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ["uuid", "status", "created_at", "updated_at", "responded_at", "user"]

    def get_user(self, obj):
        request = self.context["request"]
        user = obj.addressee
        profile = getattr(user, "profile", None)
        avatar_url = None
        avatar = getattr(profile, "avatar", None)
        if avatar:
            try:
                avatar_url = avatar.url
            except Exception:
                avatar_url = None
        if request and avatar_url:
            avatar_url = request.build_absolute_uri(avatar_url)

        return {
            "uuid": user.uuid,
            "email": user.email,
            "display_name": getattr(profile, "display_name", "") or user.email.split("@")[0],
            "tag": getattr(profile, "tag", "") if profile else "",
            "avatar_url": avatar_url,
            "is_online": bool(getattr(profile, "is_online", False)) if profile else False,
            "custom_status": getattr(profile, "custom_status", "") if profile else "",
        }


class CreateFriendRequestSerializer(serializers.Serializer):
    user_uuid = serializers.UUIDField()
