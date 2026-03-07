from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from src.apps.server.models import Channel, Role, Server
from src.apps.server.serializers import (
    ChannelCreateSerializer,
    ChannelDetailSerializer,
    ServerListSerializer,
)


class ServerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServerListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user
        return (
            Server.objects.filter(models.Q(owner=user) | models.Q(members=user))
            .distinct()
            .prefetch_related("channels")
        )

    @action(detail=True, methods=["post"], url_path="channels")
    def channels(self, request, uuid=None):
        server = get_object_or_404(Server, uuid=uuid)
        if server.owner_id != request.user.pk:
            raise PermissionDenied("Only server owner can create channels.")

        serializer = ChannelCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        allowed_role_uuids = validated_data.pop("allowed_roles", [])
        is_public = validated_data["is_public"]
        if is_public:
            allowed_role_uuids = []

        roles = list(Role.objects.filter(server=server, uuid__in=allowed_role_uuids))
        if len(roles) != len(allowed_role_uuids):
            raise ValidationError({"allowed_roles": "All roles must belong to this server."})

        channel = Channel.objects.create(server=server, **validated_data)
        if roles:
            channel.allowed_roles.set(roles)

        response_serializer = ChannelDetailSerializer(channel)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
