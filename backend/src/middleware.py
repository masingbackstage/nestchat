import urllib.parse

import jwt
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


@database_sync_to_async
def get_user_from_jwt(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

        jwt_settings = getattr(settings, "SIMPLE_JWT", {})
        user_id_claim = jwt_settings.get("USER_ID_CLAIM", "user_id")
        user_id_field = jwt_settings.get("USER_ID_FIELD", "id")

        user_identifier = payload.get(user_id_claim)
        if user_identifier is None:
            return AnonymousUser()

        return User.objects.get(**{user_id_field: user_identifier})

    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return AnonymousUser()


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        query_params = urllib.parse.parse_qs(query_string)

        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await get_user_from_jwt(token)
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)
