from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def get_user_from_token(token_str):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        token = AccessToken(token_str)
        user = User.objects.get(id=token['user_id'])
        if int(token.get('token_version', -1)) != int(getattr(user, 'token_version', 0)):
            return AnonymousUser()
        return user
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Authenticate WebSocket connections.

    Supports two methods (in priority order):
    1. First-message auth: client sends {"type": "auth", "token": "<JWT>"}
       as the first message after connecting (recommended — avoids token in URL).
    2. Query-string fallback: ?token=<JWT> (kept for backward compatibility).
    """

    async def __call__(self, scope, receive, send):
        qs = parse_qs(scope.get('query_string', b'').decode())
        token_list = qs.get('token', [])
        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            # Allow anonymous connection; consumer will wait for auth message
            scope['user'] = AnonymousUser()
        return await super().__call__(scope, receive, send)
