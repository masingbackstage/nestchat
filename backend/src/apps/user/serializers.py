from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers

from ..profile.serializers import ProfileSerializer
from .models import CustomUser


class CustomRegisterSerializer(RegisterSerializer):
    username = None

    display_name = serializers.CharField(required=False, max_length=50)

    def get_cleaned_data(self):
        data = super().get_cleaned_data()
        data.pop("username", None)
        data["display_name"] = self.validated_data.get("display_name", "")
        return data

    def save(self, request):
        user = super().save(request)
        return user


class CustomUserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="uuid", read_only=True)
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = CustomUser
        fields = ("id", "email", "profile", "is_staff", "is_active", "date_joined")
