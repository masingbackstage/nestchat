import uuid

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import exceptions, permissions, viewsets
from rest_framework.response import Response

from .models import Message
from .serializers import MessageReadSerializer
from .services import ChannelNotFound, ChannelPermissionDenied, get_channel_for_user_or_raise


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageReadSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="channel_uuid",
                required=True,
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="limit",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Messages per page (1-100). Default: 50",
            ),
            OpenApiParameter(
                name="before",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Cursor token from next_before. Backward-compatible: ISO datetime is accepted.",
            ),
            OpenApiParameter(
                name="after",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Cursor token from next_after. Backward-compatible: ISO datetime is accepted.",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=OpenApiTypes.OBJECT,
                description="Paginated channel messages payload.",
            )
        },
    )
    def list(self, request, *args, **kwargs):
        channel = self.get_channel_or_raise()
        limit = self.get_limit_or_raise()
        before_cursor = self.get_cursor_or_raise("before")
        after_cursor = self.get_cursor_or_raise("after")

        if before_cursor and after_cursor:
            raise exceptions.ValidationError({"detail": "Use only one of before/after."})

        has_more_older = False
        has_more_newer = False

        if after_cursor:
            query = (
                Message.objects.filter(channel=channel)
                .select_related("author", "author__profile")
                .order_by("created_at", "uuid")
            )
            query = self.apply_after_cursor(query, after_cursor)
            rows = list(query[: limit + 1])
            has_more_newer = len(rows) > limit
            rows = rows[:limit]
            has_more_older = (
                Message.objects.filter(channel=channel, created_at__lt=rows[0].created_at).exists()
                if rows
                else False
            )
        else:
            query = (
                Message.objects.filter(channel=channel)
                .select_related("author", "author__profile")
                .order_by("-created_at", "-uuid")
            )
            if before_cursor:
                query = self.apply_before_cursor(query, before_cursor)

            rows = list(query[: limit + 1])
            has_more_older = len(rows) > limit
            rows = rows[:limit]
            rows.reverse()
            has_more_newer = (
                Message.objects.filter(channel=channel, created_at__gt=rows[-1].created_at).exists()
                if rows
                else False
            )

        serializer = self.get_serializer(rows, many=True)
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

    def get_channel_or_raise(self):
        channel_uuid = self.request.query_params.get("channel_uuid")

        if not channel_uuid:
            raise exceptions.ValidationError({"channel_uuid": "This query parameter is required."})

        try:
            return get_channel_for_user_or_raise(self.request.user, channel_uuid)
        except ChannelNotFound as exc:
            raise exceptions.NotFound(exc.detail)
        except ChannelPermissionDenied as exc:
            raise exceptions.PermissionDenied(exc.detail)

    def get_limit_or_raise(self):
        raw_limit = self.request.query_params.get("limit")
        if raw_limit is None:
            return 50

        try:
            parsed = int(raw_limit)
        except (TypeError, ValueError):
            raise exceptions.ValidationError({"limit": "Must be an integer."})

        return min(100, max(1, parsed))

    def get_cursor_or_raise(self, field_name):
        raw_value = self.request.query_params.get(field_name)
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
