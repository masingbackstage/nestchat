from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response

from src.apps.friends.models import Friendship
from src.apps.friends.serializers import (
    CreateFriendRequestSerializer,
    FriendshipRequestIncomingSerializer,
    FriendshipRequestOutgoingSerializer,
    FriendshipSerializer,
)

User = get_user_model()


class FriendViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    def list(self, request):
        friendships = (
            Friendship.objects.filter(
                Q(user_low=request.user) | Q(user_high=request.user),
                status=Friendship.Status.ACCEPTED,
            )
            .select_related(
                "user_low",
                "user_low__profile",
                "user_high",
                "user_high__profile",
            )
            .order_by("-updated_at")
        )
        serializer = FriendshipSerializer(friendships, many=True, context={"request": request})
        return Response(serializer.data)

    def destroy(self, request, uuid=None):
        friendship = Friendship.objects.filter(uuid=uuid).first()
        if not friendship:
            raise NotFound("Friend relation not found.")

        if friendship.user_low_id != request.user.pk and friendship.user_high_id != request.user.pk:
            raise PermissionDenied("Permission denied.")

        if friendship.status == Friendship.Status.ACCEPTED:
            friendship.status = Friendship.Status.CANCELED
            friendship.responded_at = timezone.now()
            friendship.save(update_fields=["status", "responded_at", "updated_at"])
            return Response({"detail": "Friend removed."}, status=status.HTTP_200_OK)

        if (
            friendship.status == Friendship.Status.PENDING
            and friendship.requester_id == request.user.pk
        ):
            friendship.status = Friendship.Status.CANCELED
            friendship.responded_at = timezone.now()
            friendship.save(update_fields=["status", "responded_at", "updated_at"])
            return Response({"detail": "Friend request canceled."}, status=status.HTTP_200_OK)

        raise ValidationError({"detail": "Cannot remove this relation in current state."})


class FriendRequestViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"

    @action(detail=False, methods=["get"], url_path="incoming")
    def incoming(self, request):
        requests = (
            Friendship.objects.filter(
                addressee=request.user,
                status=Friendship.Status.PENDING,
            )
            .select_related("requester", "requester__profile")
            .order_by("-created_at")
        )
        serializer = FriendshipRequestIncomingSerializer(
            requests,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="outgoing")
    def outgoing(self, request):
        requests = (
            Friendship.objects.filter(
                requester=request.user,
                status=Friendship.Status.PENDING,
            )
            .select_related("addressee", "addressee__profile")
            .order_by("-created_at")
        )
        serializer = FriendshipRequestOutgoingSerializer(
            requests,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)

    def create(self, request):
        serializer = CreateFriendRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = User.objects.filter(uuid=serializer.validated_data["user_uuid"]).first()
        if not target_user:
            raise NotFound("User not found.")

        if target_user.pk == request.user.pk:
            raise ValidationError({"detail": "Cannot send friend request to yourself."})

        pair_qs = Friendship.pair_queryset(request.user, target_user)
        existing = pair_qs.first()
        if existing:
            if existing.status == Friendship.Status.ACCEPTED:
                raise ValidationError({"detail": "You are already friends."})
            if existing.status == Friendship.Status.PENDING:
                raise ValidationError({"detail": "Friend request already pending."})

            existing.requester = request.user
            existing.addressee = target_user
            existing.status = Friendship.Status.PENDING
            existing.responded_at = None
            existing.save(
                update_fields=["requester", "addressee", "status", "responded_at", "updated_at"]
            )
            out = FriendshipRequestOutgoingSerializer(existing, context={"request": request})
            return Response(out.data, status=status.HTTP_201_CREATED)

        user_low, user_high = Friendship.normalize_pair(request.user, target_user)
        created = Friendship.objects.create(
            user_low=user_low,
            user_high=user_high,
            requester=request.user,
            addressee=target_user,
            status=Friendship.Status.PENDING,
        )
        out = FriendshipRequestOutgoingSerializer(created, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, uuid=None):
        relation = Friendship.objects.filter(uuid=uuid).first()
        if not relation:
            raise NotFound("Friend request not found.")

        if relation.status != Friendship.Status.PENDING:
            raise ValidationError({"detail": "Friend request is not pending."})
        if relation.addressee_id != request.user.pk:
            raise PermissionDenied("Permission denied.")

        relation.status = Friendship.Status.ACCEPTED
        relation.responded_at = timezone.now()
        relation.save(update_fields=["status", "responded_at", "updated_at"])
        out = FriendshipSerializer(relation, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, uuid=None):
        relation = Friendship.objects.filter(uuid=uuid).first()
        if not relation:
            raise NotFound("Friend request not found.")

        if relation.status != Friendship.Status.PENDING:
            raise ValidationError({"detail": "Friend request is not pending."})
        if relation.addressee_id != request.user.pk:
            raise PermissionDenied("Permission denied.")

        relation.status = Friendship.Status.DECLINED
        relation.responded_at = timezone.now()
        relation.save(update_fields=["status", "responded_at", "updated_at"])
        return Response({"detail": "Friend request declined."}, status=status.HTTP_200_OK)
