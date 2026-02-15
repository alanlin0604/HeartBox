from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    scope = 'login'


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
