from rest_framework import viewsets, permissions, exceptions
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Message
from .serializers import MessageReadSerializer
from .services import (
    ChannelNotFound,
    ChannelPermissionDenied,
    get_channel_for_user_or_raise,
)


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='channel_uuid',
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        channel_uuid = self.request.query_params.get('channel_uuid')

        if not channel_uuid:
            return Message.objects.none()

        try:
            channel = get_channel_for_user_or_raise(self.request.user, channel_uuid)
        except ChannelNotFound as exc:
            raise exceptions.NotFound(exc.detail)
        except ChannelPermissionDenied as exc:
            raise exceptions.PermissionDenied(exc.detail)

        return Message.objects.filter(channel=channel).select_related('author', 'author__profile').order_by('created_at')
