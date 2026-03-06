from rest_framework import serializers
from .models.server import Server
from .models.channel import Channel

class ChannelShortSerializer(serializers.ModelSerializer):

    class Meta:
        model = Channel
        fields = ['uuid', 'name', 'channel_type']

class ServerListSerializer(serializers.ModelSerializer):
    channels = ChannelShortSerializer(many=True, read_only=True)

    class Meta:
        model = Server
        fields = ['uuid', 'name', 'channels']
