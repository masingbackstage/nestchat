from rest_framework import serializers
from .models import Profile

class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = (
            'uuid',
            'display_name',
            'avatar',
            'bio',
            'tag',
            'theme_color',
            'custom_status',
            'is_online'
        )
        read_only_fields = ('uuid', 'tag', 'is_online')