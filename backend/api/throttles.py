import hashlib

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


class LoginPerUsernameThrottle(SimpleRateThrottle):
    """Account-targeted login throttle.

    AnonRateThrottle keys on IP, which a botnet can rotate. This throttle
    keys on the *attempted* identifier so 50 failed logins against
    alice@example.com block further attempts regardless of source IP.
    Falls back to anon throttling if no identifier is present.
    """
    scope = 'login_per_username'

    def get_cache_key(self, request, view):
        attempted = request.data.get('email') or request.data.get('username') or ''
        attempted = attempted.strip().lower()
        if not attempted:
            return None
        # Hash to keep raw emails out of cache keys.
        h = hashlib.sha256(attempted.encode()).hexdigest()[:24]
        return self.cache_format % {'scope': self.scope, 'ident': h}


class RegisterRateThrottle(AnonRateThrottle):
    scope = 'register'


class PasswordResetRateThrottle(AnonRateThrottle):
    scope = 'password_reset'


class NoteCreateThrottle(UserRateThrottle):
    scope = 'note_create'


class UploadThrottle(UserRateThrottle):
    scope = 'upload'


class ExportThrottle(UserRateThrottle):
    scope = 'export'


class BookingThrottle(UserRateThrottle):
    scope = 'booking'


class MessageThrottle(UserRateThrottle):
    scope = 'message_send'


class AIChatThrottle(UserRateThrottle):
    scope = 'ai_chat'


class DeleteAccountThrottle(UserRateThrottle):
    scope = 'delete_account'


class RefreshTokenThrottle(AnonRateThrottle):
    scope = 'token_refresh'


class GeneralWriteThrottle(UserRateThrottle):
    scope = 'general_write'
