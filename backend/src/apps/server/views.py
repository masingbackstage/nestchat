from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db import models
from .models import Server
from .serializers import ServerListSerializer

class ServerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServerListSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        user = self.request.user
        return Server.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct().prefetch_related('channels') 
