from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

User = get_user_model()


class LogoutSessionSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LogoutAllSessionsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tokens = OutstandingToken.objects.filter(user=request.user)
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)

        return Response(
            {"detail": "All refresh tokens have been revoked."}, status=status.HTTP_200_OK
        )


class LogoutSessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]

        try:
            token = RefreshToken(refresh_token)
            if str(token.get("user_uuid")) != str(request.user.uuid):
                return Response(
                    {"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST
                )
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"detail": "Session logged out."}, status=status.HTTP_200_OK)


class UserSearchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        self.throttle_scope = "user_search"
        return super().get_throttles()

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response([])

        users = (
            User.objects.exclude(pk=request.user.pk)
            .select_related("profile")
            .filter(
                Q(email__icontains=query)
                | Q(profile__display_name__icontains=query)
                | Q(profile__tag__icontains=query)
            )
            .order_by("email")[:20]
        )

        payload = []
        for user in users:
            profile = getattr(user, "profile", None)
            avatar_url = None
            avatar = getattr(profile, "avatar", None)
            if avatar:
                try:
                    avatar_url = request.build_absolute_uri(avatar.url)
                except Exception:
                    avatar_url = None

            payload.append(
                {
                    "uuid": str(user.uuid),
                    "email": user.email,
                    "display_name": getattr(profile, "display_name", "")
                    or user.email.split("@")[0],
                    "tag": getattr(profile, "tag", "") if profile else "",
                    "avatar_url": avatar_url,
                    "is_online": bool(getattr(profile, "is_online", False)) if profile else False,
                    "custom_status": getattr(profile, "custom_status", "") if profile else "",
                }
            )

        return Response(payload)
