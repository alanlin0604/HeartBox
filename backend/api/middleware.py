import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)


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


class UserTimezoneMiddleware:
    """Activate the authenticated user's timezone for each request.

    DRF JWT authentication happens at the view layer (after middleware),
    so we parse the JWT token directly from the Authorization header to
    look up the user's timezone and activate it before the view runs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.utils import timezone as tz
        tz.deactivate()  # Start with server default

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            try:
                from django.contrib.auth import get_user_model
                token = AccessToken(auth_header.split(' ', 1)[1])
                User = get_user_model()
                user_tz = User.objects.filter(id=token['user_id']).values_list('timezone', flat=True).first()
                if user_tz:
                    import zoneinfo
                    tz.activate(zoneinfo.ZoneInfo(user_tz))
            except Exception:
                # Token expired / malformed / user gone — fall back to server tz silently.
                # Logging at debug since this fires on every anon request too.
                logger.debug('TimezoneMiddleware: could not resolve user tz', exc_info=True)

        response = self.get_response(request)
        tz.deactivate()
        return response


class ContentSecurityPolicyMiddleware:
    """Injects Content-Security-Policy header from CSP_* settings."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp_header = self._build_header()

    @staticmethod
    def _build_header():
        directives = []
        mapping = {
            'CSP_DEFAULT_SRC': 'default-src',
            'CSP_SCRIPT_SRC': 'script-src',
            'CSP_STYLE_SRC': 'style-src',
            'CSP_IMG_SRC': 'img-src',
            'CSP_CONNECT_SRC': 'connect-src',
            'CSP_FONT_SRC': 'font-src',
            'CSP_FRAME_ANCESTORS': 'frame-ancestors',
        }
        for setting_name, directive in mapping.items():
            values = getattr(settings, setting_name, None)
            if values:
                directives.append(f"{directive} {' '.join(values)}")
        return '; '.join(directives) if directives else None

    def __call__(self, request):
        response = self.get_response(request)
        if self.csp_header:
            response['Content-Security-Policy'] = self.csp_header
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response
