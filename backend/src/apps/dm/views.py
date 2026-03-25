import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import exceptions, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from src.apps.dm.models import (
    DMConversation,
    DMConversationParticipant,
    DMMessage,
    DMMessageReaction,
)
from src.apps.dm.serializers import (
    CreateDirectDMConversationSerializer,
    CreateDMConversationSerializer,
    CreateDMMessageSerializer,
    DMConversationListItemSerializer,
    DMMessageReadSerializer,
    MarkDMConversationReadSerializer,
    ToggleDMReactionSerializer,
    UpdateDMMessageSerializer,
)
from src.apps.dm.services import (
    DMConversationNotFound,
    DMConversationPermissionDenied,
    DMMessageNotFound,
    DMMessagePermissionDenied,
    can_edit_or_delete_dm_message,
    get_dm_conversation_for_user_or_raise,
    get_dm_message_for_user_or_raise,
)
from src.apps.friends.models import Friendship

User = get_user_model()


class DMConversationViewSet(
    viewsets.GenericViewSet, mixins.ListModelMixin, mixins.CreateModelMixin
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DMConversationListItemSerializer
    lookup_field = "uuid"
    queryset = DMConversation.objects.none()

    def get_queryset(self):
        return (
            DMConversation.objects.filter(conversation_participants__user=self.request.user)
            .distinct()
            .prefetch_related(
                "conversation_participants__user",
                "conversation_participants__user__profile",
            )
            .order_by("-updated_at")
        )

    def list(self, request, *args, **kwargs):
        conversations = list(self.get_queryset())
        participant_map = {
            participant.conversation_id: participant
            for participant in DMConversationParticipant.objects.select_related(
                "last_read_message"
            ).filter(conversation__in=conversations, user=request.user)
        }

        for conversation in conversations:
            last_message = (
                DMMessage.objects.filter(conversation=conversation)
                .select_related("author", "author__profile")
                .prefetch_related("reactions")
                .order_by("-created_at", "-uuid")
                .first()
            )
            setattr(conversation, "_prefetched_last_message", last_message)

            participant = participant_map.get(conversation.pk)
            unread_count = 0
            if participant and participant.last_read_message_id:
                marker = participant.last_read_message
                unread_count = (
                    DMMessage.objects.filter(conversation=conversation)
                    .filter(
                        Q(created_at__gt=marker.created_at)
                        | Q(created_at=marker.created_at, uuid__gt=marker.uuid)
                    )
                    .count()
                )
            else:
                unread_count = DMMessage.objects.filter(conversation=conversation).count()

            setattr(conversation, "unread_count", unread_count)

        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = CreateDMConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_uuids = serializer.validated_data["participant_uuids"]
        title = serializer.validated_data.get("title")

        users = list(User.objects.filter(uuid__in=participant_uuids))
        if len(users) != len(participant_uuids):
            raise exceptions.ValidationError({"participant_uuids": "Some users were not found."})

        participant_ids = {user.pk for user in users}
        participant_ids.add(request.user.pk)

        if len(participant_ids) == 2:
            participant_uuid_values = sorted(str(item.uuid) for item in users + [request.user])
            direct_key = "::".join(sorted(set(participant_uuid_values)))
            conversation, created = DMConversation.objects.get_or_create(
                direct_key=direct_key,
                defaults={
                    "conversation_type": DMConversation.TYPE_DIRECT,
                    "created_by": request.user,
                    "title": None,
                },
            )
            if created:
                for user_id in participant_ids:
                    DMConversationParticipant.objects.create(
                        conversation=conversation,
                        user_id=user_id,
                    )
        else:
            if len(participant_ids) < 3:
                raise exceptions.ValidationError(
                    {
                        "participant_uuids": "Group DM requires at least 3 participants including you."
                    }
                )
            conversation = DMConversation.objects.create(
                conversation_type=DMConversation.TYPE_GROUP,
                title=title or None,
                created_by=request.user,
            )
            DMConversationParticipant.objects.bulk_create(
                [
                    DMConversationParticipant(conversation=conversation, user_id=user_id)
                    for user_id in participant_ids
                ]
            )

        response_serializer = DMConversationListItemSerializer(
            conversation, context=self.get_serializer_context()
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="direct")
    @transaction.atomic
    def create_direct(self, request):
        serializer = CreateDirectDMConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = User.objects.filter(uuid=serializer.validated_data["user_uuid"]).first()
        if not target_user:
            raise exceptions.NotFound("User not found.")
        if target_user.pk == request.user.pk:
            raise exceptions.ValidationError(
                {"detail": "Cannot create direct conversation with yourself."}
            )

        friendship = Friendship.pair_queryset(request.user, target_user).first()
        if not friendship or friendship.status != Friendship.Status.ACCEPTED:
            raise exceptions.PermissionDenied(
                "Direct conversation is allowed only with accepted friends."
            )

        participant_uuid_values = sorted([str(request.user.uuid), str(target_user.uuid)])
        direct_key = "::".join(participant_uuid_values)
        conversation, created = DMConversation.objects.get_or_create(
            direct_key=direct_key,
            defaults={
                "conversation_type": DMConversation.TYPE_DIRECT,
                "created_by": request.user,
                "title": None,
            },
        )
        if created:
            DMConversationParticipant.objects.bulk_create(
                [
                    DMConversationParticipant(conversation=conversation, user=request.user),
                    DMConversationParticipant(conversation=conversation, user=target_user),
                ]
            )

        response_serializer = DMConversationListItemSerializer(
            conversation,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, uuid=None):
        try:
            conversation = get_dm_conversation_for_user_or_raise(request.user, uuid)
        except DMConversationNotFound as exc:
            raise exceptions.NotFound(exc.detail)
        except DMConversationPermissionDenied as exc:
            raise exceptions.PermissionDenied(exc.detail)

        if request.method.lower() == "post":
            payload = CreateDMMessageSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            message = DMMessage.objects.create(
                conversation=conversation,
                author=request.user,
                content=payload.validated_data["content"],
            )
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=["updated_at"])
            serializer = DMMessageReadSerializer(message, context=self.get_serializer_context())
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        limit = self.get_limit_or_raise(request)
        before_cursor = self.get_cursor_or_raise(request, "before")
        after_cursor = self.get_cursor_or_raise(request, "after")

        if before_cursor and after_cursor:
            raise exceptions.ValidationError({"detail": "Use only one of before/after."})

        has_more_older = False
        has_more_newer = False

        if after_cursor:
            query = (
                DMMessage.objects.filter(conversation=conversation)
                .select_related("author", "author__profile")
                .prefetch_related("reactions")
                .order_by("created_at", "uuid")
            )
            query = self.apply_after_cursor(query, after_cursor)
            rows = list(query[: limit + 1])
            has_more_newer = len(rows) > limit
            rows = rows[:limit]
            has_more_older = (
                DMMessage.objects.filter(
                    conversation=conversation, created_at__lt=rows[0].created_at
                ).exists()
                if rows
                else False
            )
        else:
            query = (
                DMMessage.objects.filter(conversation=conversation)
                .select_related("author", "author__profile")
                .prefetch_related("reactions")
                .order_by("-created_at", "-uuid")
            )
            if before_cursor:
                query = self.apply_before_cursor(query, before_cursor)

            rows = list(query[: limit + 1])
            has_more_older = len(rows) > limit
            rows = rows[:limit]
            rows.reverse()
            has_more_newer = (
                DMMessage.objects.filter(
                    conversation=conversation, created_at__gt=rows[-1].created_at
                ).exists()
                if rows
                else False
            )

        serializer = DMMessageReadSerializer(rows, many=True, context=self.get_serializer_context())
        next_before = self.build_cursor(rows[0]) if rows else None
        next_after = self.build_cursor(rows[-1]) if rows else None

        return Response(
            {
                "items": serializer.data,
                "has_more_older": has_more_older,
                "has_more_newer": has_more_newer,
                "next_before": next_before,
                "next_after": next_after,
            }
        )

    @action(detail=True, methods=["post"], url_path="read-state")
    def mark_read(self, request, uuid=None):
        try:
            conversation = get_dm_conversation_for_user_or_raise(request.user, uuid)
        except DMConversationNotFound as exc:
            raise exceptions.NotFound(exc.detail)
        except DMConversationPermissionDenied as exc:
            raise exceptions.PermissionDenied(exc.detail)

        serializer = MarkDMConversationReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        last_read_message_uuid = serializer.validated_data.get("last_read_message_uuid")

        participant = DMConversationParticipant.objects.get(
            conversation=conversation,
            user=request.user,
        )

        if last_read_message_uuid:
            try:
                message = DMMessage.objects.get(
                    uuid=last_read_message_uuid,
                    conversation=conversation,
                )
            except DMMessage.DoesNotExist as exc:
                raise exceptions.ValidationError(
                    {"last_read_message_uuid": "Message does not belong to this conversation."}
                ) from exc
            participant.last_read_message = message
        else:
            participant.last_read_message = (
                DMMessage.objects.filter(conversation=conversation)
                .order_by("-created_at", "-uuid")
                .first()
            )
        participant.save(update_fields=["last_read_message"])
        return Response({"detail": "Read state updated."}, status=status.HTTP_200_OK)

    def get_limit_or_raise(self, request):
        raw_limit = request.query_params.get("limit")
        if raw_limit is None:
            return 50

        try:
            parsed = int(raw_limit)
        except (TypeError, ValueError):
            raise exceptions.ValidationError({"limit": "Must be an integer."})

        return min(100, max(1, parsed))

    def get_cursor_or_raise(self, request, field_name):
        raw_value = request.query_params.get(field_name)
        if not raw_value:
            return None

        datetime_raw, uuid_raw = self.split_cursor(raw_value)
        parsed = parse_datetime(datetime_raw)
        if not parsed:
            raise exceptions.ValidationError({field_name: "Must be a valid ISO datetime."})
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone=timezone.utc)

        parsed_uuid = None
        if uuid_raw is not None:
            try:
                parsed_uuid = uuid.UUID(uuid_raw)
            except ValueError:
                raise exceptions.ValidationError(
                    {field_name: "Must be a valid cursor token (iso_datetime|uuid)."}
                )

        return parsed, parsed_uuid

    def split_cursor(self, raw_cursor):
        if "|" not in raw_cursor:
            return raw_cursor, None
        datetime_raw, uuid_raw = raw_cursor.split("|", 1)
        return datetime_raw, uuid_raw

    def apply_before_cursor(self, queryset, cursor):
        cursor_dt, cursor_uuid = cursor
        if cursor_uuid is None:
            return queryset.filter(created_at__lt=cursor_dt)
        return queryset.filter(
            Q(created_at__lt=cursor_dt) | Q(created_at=cursor_dt, uuid__lt=cursor_uuid)
        )

    def apply_after_cursor(self, queryset, cursor):
        cursor_dt, cursor_uuid = cursor
        if cursor_uuid is None:
            return queryset.filter(created_at__gt=cursor_dt)
        return queryset.filter(
            Q(created_at__gt=cursor_dt) | Q(created_at=cursor_dt, uuid__gt=cursor_uuid)
        )

    def build_cursor(self, message):
        return f"{message.created_at.isoformat()}|{message.uuid}"


class DMMessageViewSet(
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DMMessageReadSerializer
    lookup_field = "uuid"
    queryset = DMMessage.objects.none()

    def get_object(self):
        try:
            return get_dm_message_for_user_or_raise(self.request.user, self.kwargs.get("uuid"))
        except DMMessageNotFound as exc:
            raise exceptions.NotFound(exc.detail)
        except DMMessagePermissionDenied as exc:
            raise exceptions.PermissionDenied(exc.detail)

    def partial_update(self, request, *args, **kwargs):
        message = self.get_object()
        if not can_edit_or_delete_dm_message(request.user, message):
            raise exceptions.PermissionDenied("Permission denied.")
        if message.is_deleted:
            raise exceptions.ValidationError({"detail": "Cannot edit deleted message."})

        serializer = UpdateDMMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message.content = serializer.validated_data["content"]
        message.edited_at = timezone.now()
        message.save(update_fields=["content", "edited_at", "updated_at"])
        return Response(
            DMMessageReadSerializer(message, context=self.get_serializer_context()).data
        )

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if not can_edit_or_delete_dm_message(request.user, message):
            raise exceptions.PermissionDenied("Permission denied.")

        if not message.is_deleted:
            message.is_deleted = True
            message.deleted_at = timezone.now()
            message.deleted_by = request.user
            message.content = ""
            message.save(
                update_fields=["is_deleted", "deleted_at", "deleted_by", "content", "updated_at"]
            )

        return Response(
            DMMessageReadSerializer(message, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="reactions/toggle")
    def toggle_reaction(self, request, *args, **kwargs):
        message = self.get_object()
        if message.is_deleted:
            raise exceptions.ValidationError({"detail": "Cannot react to deleted message."})

        serializer = ToggleDMReactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emoji = serializer.validated_data["emoji"]

        reaction = DMMessageReaction.objects.filter(
            message=message,
            user=request.user,
            emoji=emoji,
        ).first()
        if reaction:
            reaction.delete()
        else:
            DMMessageReaction.objects.create(message=message, user=request.user, emoji=emoji)

        message.refresh_from_db()
        return Response(
            DMMessageReadSerializer(message, context=self.get_serializer_context()).data
        )
