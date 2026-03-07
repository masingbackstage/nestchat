from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


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
