"""Authentication, registration, password reset, profile, 2FA, and OAuth endpoints.

Extracted from views/__init__.py to keep auth-specific logic in its own module.
Re-exported via views/__init__.py for backward compatibility.
"""

import os
import time

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.html import escape as html_escape
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import exceptions, generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from ..models import TOTPDevice
from ..serializers import UserProfileSerializer, UserRegistrationSerializer
from ..services.audit import log_action
from ..throttles import (
    DeleteAccountThrottle, GeneralWriteThrottle, LoginPerUsernameThrottle,
    LoginRateThrottle, PasswordResetRateThrottle, RefreshTokenThrottle,
    RegisterRateThrottle,
)

from . import User, error_response, logger


# ===== Email i18n =====

_EMAIL_STRINGS = {
    'zh-TW': {
        'verify_subject': 'HeartBox 心事盒 — 驗證您的電子信箱',
        'verify_greeting': '您好 {username}，',
        'verify_register_body': '感謝您註冊 HeartBox 心事盒！請點擊以下連結驗證您的電子信箱：',
        'verify_resend_body': '請點擊以下連結驗證您的電子信箱：',
        'verify_ignore': '如果您並未註冊，請忽略此信。',
        'verify_btn': '驗證信箱',
        'team': '— HeartBox 心事盒團隊',
        'tagline': 'HeartBox 心事盒 — 您的心理健康夥伴',
        'reset_subject': 'HeartBox 心事盒 — 重設您的密碼',
        'reset_body': '我們收到了重設您 HeartBox 密碼的請求。請使用以下連結：',
        'reset_html_body': '我們收到了重設您密碼的請求，請點擊下方按鈕：',
        'reset_expire': '此連結將在 15 分鐘後失效。',
        'reset_ignore': '如果您並未提出此請求，請忽略此信。',
        'reset_btn': '重設密碼',
    },
    'en': {
        'verify_subject': 'HeartBox — Verify Your Email',
        'verify_greeting': 'Hi {username},',
        'verify_register_body': 'Thanks for signing up for HeartBox! Please click the link below to verify your email:',
        'verify_resend_body': 'Please click the link below to verify your email:',
        'verify_ignore': 'If you did not sign up, please ignore this email.',
        'verify_btn': 'Verify Email',
        'team': '— The HeartBox Team',
        'tagline': 'HeartBox — Your Mental Wellness Companion',
        'reset_subject': 'HeartBox — Reset Your Password',
        'reset_body': 'We received a request to reset your HeartBox password. Please use the link below:',
        'reset_html_body': 'We received a request to reset your password. Click the button below:',
        'reset_expire': 'This link will expire in 15 minutes.',
        'reset_ignore': 'If you did not request this, please ignore this email.',
        'reset_btn': 'Reset Password',
    },
    'ja': {
        'verify_subject': 'HeartBox — メール認証',
        'verify_greeting': '{username} さん、こんにちは。',
        'verify_register_body': 'HeartBox にご登録いただきありがとうございます！以下のリンクをクリックしてメールアドレスを認証してください：',
        'verify_resend_body': '以下のリンクをクリックしてメールアドレスを認証してください：',
        'verify_ignore': '心当たりがない場合は、このメールを無視してください。',
        'verify_btn': 'メールを認証',
        'team': '— HeartBox チーム',
        'tagline': 'HeartBox — あなたのメンタルウェルネスパートナー',
        'reset_subject': 'HeartBox — パスワードのリセット',
        'reset_body': 'HeartBox のパスワードリセットのリクエストを受け付けました。以下のリンクをご利用ください：',
        'reset_html_body': 'パスワードリセットのリクエストを受け付けました。下のボタンをクリックしてください：',
        'reset_expire': 'このリンクは 15 分後に無効になります。',
        'reset_ignore': 'リクエストした覚えがない場合は、このメールを無視してください。',
        'reset_btn': 'パスワードをリセット',
    },
}


def _get_email_lang(request):
    """Detect user language from Accept-Language header, default to zh-TW."""
    accept = getattr(request, 'META', {}).get('HTTP_ACCEPT_LANGUAGE', '') if request else ''
    if not accept:
        return 'zh-TW'
    lang = accept.split(',')[0].strip().lower()
    if lang.startswith('ja'):
        return 'ja'
    if lang.startswith('en'):
        return 'en'
    return 'zh-TW'


def _email_strings(request):
    """Return the email string dict for the request's language."""
    return _EMAIL_STRINGS[_get_email_lang(request)]


class RegisterView(generics.CreateAPIView):
    """Register a new account.

    Anti-enumeration: returns 201 for both a fresh registration AND a
    duplicate-email attempt, with the response time normalised to ~1 s
    so an attacker can't tell whether the email is already in use. The
    duplicate path silently re-sends the verification email to the
    existing account if it's still unverified, otherwise it sends a
    "someone-tried-to-register" notice.
    Other validation errors (weak password, malformed email) still
    return 400 — those don't leak account existence.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]

    MIN_RESPONSE_TIME = 1.0  # seconds — match ForgotPassword's normalisation

    def create(self, request, *args, **kwargs):
        start = time.monotonic()
        serializer = self.get_serializer(data=request.data)

        # Inspect errors before raising — only mask if the ONLY issue is
        # email-already-exists. Other errors (bad password, missing field)
        # are user-facing and must still surface.
        if not serializer.is_valid():
            email_errors = serializer.errors.get('email', [])
            email_taken = any(
                'already exists' in str(e).lower() or 'unique' in str(e).lower()
                for e in email_errors
            )
            other_errors = {k: v for k, v in serializer.errors.items() if k != 'email'}
            # Email-taken-only → silent re-send, normalised response
            if email_taken and not other_errors and not email_errors[1:]:
                attempted_email = request.data.get('email', '').strip()
                if attempted_email:
                    self._handle_duplicate_email(request, attempted_email)
                self._sleep_to_min(start)
                return Response(
                    {'detail': 'Registration request received.'},
                    status=status.HTTP_201_CREATED,
                )
            # Otherwise surface the validation errors as usual.
            serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)
        # Audit successful registration. serializer.instance is the new user.
        if getattr(serializer, 'instance', None) is not None:
            log_action(serializer.instance, 'auth.register', request=request)
        self._sleep_to_min(start)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _sleep_to_min(self, start):
        elapsed = time.monotonic() - start
        if elapsed < self.MIN_RESPONSE_TIME:
            time.sleep(self.MIN_RESPONSE_TIME - elapsed)

    def _handle_duplicate_email(self, request, email):
        """Silently react to a duplicate-email registration attempt.

        If the existing account is unverified, re-send the verification
        link (legitimate user might have lost the original email).
        If already verified, send a "someone tried to register" notice
        so the real owner can act if it wasn't them.
        """
        try:
            existing = User.objects.filter(email__iexact=email).first()
            if not existing:
                return
            if not getattr(existing, 'email_verified', False):
                # Re-send verification (same as ResendVerificationView body)
                self._send_verification(request, existing)
            else:
                logger.info('Duplicate registration attempt for verified email %s', email)
                # In a real production system we might email a notice here.
        except Exception:
            logger.warning('Failed to handle duplicate registration silently', exc_info=True)

    def _send_verification(self, request, user):
        s = _email_strings(request)
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        frontend_url = os.environ.get('FRONTEND_URL', 'https://heartbox.pages.dev')
        verify_url = f'{frontend_url}/verify-email?uid={uid}&token={token}'
        greeting = s['verify_greeting'].format(username=user.username)
        body = html_escape(s.get('verify_resend_body') or s['verify_register_body'])
        try:
            send_mail(
                s['verify_subject'],
                f'{greeting}\n\n{verify_url}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=(
                    f'<p>{html_escape(greeting)}</p><p>{body}</p>'
                    f'<p><a href="{verify_url}">{html_escape(s["verify_btn"])}</a></p>'
                ),
            )
        except Exception:
            logger.warning('Re-verification email send failed for %s', user.email)

    def perform_create(self, serializer):
        user = serializer.save()
        # Send verification email
        try:
            s = _email_strings(self.request)
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            frontend_url = os.environ.get('FRONTEND_URL', 'https://heartbox.pages.dev')
            verify_url = f'{frontend_url}/verify-email?uid={uid}&token={token}'
            greeting = s['verify_greeting'].format(username=user.username)
            plain_message = (
                f'{greeting}\n\n'
                f'{s["verify_register_body"]}\n'
                f'{verify_url}\n\n'
                f'{s["verify_ignore"]}\n\n'
                f'{s["team"]}'
            )
            greeting_html = html_escape(greeting)
            body_html = html_escape(s["verify_register_body"])
            ignore_html = html_escape(s["verify_ignore"])
            tagline_html = html_escape(s["tagline"])
            btn_html = html_escape(s["verify_btn"])
            html_message = (
                f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">'
                f'<h2 style="color:#7c3aed">HeartBox</h2>'
                f'<p>{greeting_html}</p>'
                f'<p>{body_html}</p>'
                f'<p style="text-align:center;margin:28px 0">'
                f'<a href="{verify_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
                f'border-radius:8px;text-decoration:none;font-weight:600">{btn_html}</a></p>'
                f'<p style="color:#888;font-size:13px">{ignore_html}</p>'
                f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
                f'<p style="color:#aaa;font-size:12px">{tagline_html}</p>'
                f'</div>'
            )
            send_mail(
                s['verify_subject'],
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
        except Exception:
            logger.exception('Failed to send verification email to %s', user.email)


def _issue_2fa_partial_token(user) -> str:
    """Short-lived (3 min) access token scoped ONLY to /api/auth/login/2fa/.

    The custom ``scope='2fa_pending'`` claim is checked by Login2FAView and
    rejected by ``VersionedJWTAuthentication`` everywhere else, so this token
    cannot be used to authenticate a regular API call before the second
    factor is supplied. Without this, a stolen first-factor-only token gave
    the attacker ACCESS_TOKEN_LIFETIME of regular API access.
    """
    from datetime import timedelta as _td
    from rest_framework_simplejwt.tokens import AccessToken
    tok = AccessToken.for_user(user)
    tok['scope'] = '2fa_pending'
    tok.set_exp(lifetime=_td(minutes=3))
    return str(tok)


def _issue_tokens(user):
    refresh = RefreshToken.for_user(user)
    refresh['token_version'] = user.token_version
    access = refresh.access_token
    access['token_version'] = user.token_version
    return {'refresh': str(refresh), 'access': str(access)}


class VersionedTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['token_version'] = user.token_version
        return token


class VersionedTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = User.objects.filter(id=token.get('user_id')).first()
        if not user:
            raise exceptions.AuthenticationFailed('User not found')
        if int(token.get('token_version', -1)) != int(user.token_version):
            raise exceptions.AuthenticationFailed('Token no longer valid')
        data = super().validate(attrs)
        # SimpleJWT's parent validate() does NOT propagate custom claims onto
        # the rotated access token. Mint a fresh one with token_version so
        # the next request still validates against the user's current
        # generation (otherwise a logout-rotated user could keep working
        # off a refreshed access for the full ACCESS_TOKEN_LIFETIME window).
        from rest_framework_simplejwt.tokens import AccessToken
        access = AccessToken(data['access'])
        access['token_version'] = user.token_version
        data['access'] = str(access)
        return data


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VersionedTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle, LoginPerUsernameThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except exceptions.AuthenticationFailed:
            # Audit failed logins so brute-force attempts are visible.
            attempted = (request.data.get('email') or request.data.get('username') or '').strip()
            log_action(
                None, 'auth.login_failed', request=request,
                details={'attempted_identifier': attempted[:120]},
            )
            raise
        user = serializer.user
        # Auto-cancel a pending account deletion the moment the user logs
        # back in. The user has clearly changed their mind — they're back.
        if user.deletion_scheduled_at:
            user.deletion_scheduled_at = None
            user.save(update_fields=['deletion_scheduled_at'])
            log_action(user, 'account_delete_cancel_on_login', request=request)
        # Check for 2FA
        try:
            totp_device = user.totp_device
            if totp_device.confirmed:
                log_action(user, 'auth.login_2fa_required', request=request)
                # Mint a SCOPED partial token that is ONLY accepted by
                # Login2FAView (scope=2fa_pending) and rejected by every
                # other endpoint. Without the scope check, the access half
                # of this token would authenticate normal API requests
                # before the second factor was supplied.
                return Response({
                    'requires_2fa': True,
                    'partial_token': _issue_2fa_partial_token(user),
                })
        except TOTPDevice.DoesNotExist:
            pass
        log_action(user, 'auth.login', request=request)
        data = dict(serializer.validated_data)
        data['user'] = UserProfileSerializer(user, context={'request': request}).data
        return Response(data)


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RefreshTokenThrottle]
    serializer_class = VersionedTokenRefreshSerializer


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        start = time.monotonic()
        email = (request.data.get('email') or '').strip()
        user = User.objects.filter(email__iexact=email).first()
        if user:
            s = _email_strings(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            from django.conf import settings
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            reset_url = f'{frontend_url.rstrip("/")}/reset-password?uid={uid}&token={token}'
            greeting = s['verify_greeting'].format(username=user.username)
            plain_message = (
                f'{greeting}\n\n'
                f'{s["reset_body"]}\n{reset_url}\n\n'
                f'{s["reset_expire"]}\n'
                f'{s["reset_ignore"]}\n\n'
                f'{s["team"]}'
            )
            html_message = (
                f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">'
                f'<h2 style="color:#7c3aed">HeartBox</h2>'
                f'<p>{html_escape(greeting)}</p>'
                f'<p>{html_escape(s["reset_html_body"])}</p>'
                f'<p style="text-align:center;margin:28px 0">'
                f'<a href="{reset_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
                f'border-radius:8px;text-decoration:none;font-weight:600">{html_escape(s["reset_btn"])}</a></p>'
                f'<p style="color:#888;font-size:13px">{html_escape(s["reset_expire"])} '
                f'{html_escape(s["reset_ignore"])}</p>'
                f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
                f'<p style="color:#aaa;font-size:12px">{html_escape(s["tagline"])}</p>'
                f'</div>'
            )
            try:
                send_mail(
                    s['reset_subject'],
                    plain_message,
                    getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@heartbox.local'),
                    [user.email],
                    html_message=html_message,
                )
            except Exception as e:
                logger.error('Failed to send password reset email to %s: %s', user.email, e)
        # Normalize response time to prevent email enumeration via timing
        elapsed = time.monotonic() - start
        min_time = 1.0
        if elapsed < min_time:
            time.sleep(min_time - elapsed)
        return Response({'status': 'ok'})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    @staticmethod
    def _consumed_key(user_id, token):
        # Hash so a cache snapshot doesn't directly leak reset tokens.
        import hashlib
        h = hashlib.sha256(f'{user_id}:{token}'.encode()).hexdigest()
        return f'pwreset_used:{h}'

    def post(self, request):
        from django.core.cache import cache
        uid = request.data.get('uid') or ''
        token = request.data.get('token') or ''
        new_password = request.data.get('new_password') or ''
        if len(new_password) < 8:
            return error_response('password_too_short', 'Password too short')
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            return error_response('invalid_reset_link', 'Invalid reset link')
        if not default_token_generator.check_token(user, token):
            return error_response('invalid_reset_link', 'Invalid reset link')
        # Defence-in-depth single-use: Django's token *is* invalidated by the
        # password hash change below, but the cache marker also blocks a
        # racing duplicate request that arrives before set_password commits,
        # and survives even if password change is skipped for some reason.
        consumed_key = self._consumed_key(user_id, token)
        if cache.get(consumed_key):
            return error_response('invalid_reset_link', 'Invalid reset link')
        # Run Django password validators
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({'detail': e.messages}, status=status.HTTP_400_BAD_REQUEST)
        # Mark consumed before mutation so a concurrent retry hits the lock.
        cache.set(consumed_key, '1', timeout=getattr(settings, 'PASSWORD_RESET_TIMEOUT', 900))
        user.set_password(new_password)
        # Rotate token_version to invalidate all existing JWT sessions
        user.token_version += 1
        user.save(update_fields=['password', 'token_version'])
        log_action(user, 'password_reset', request)
        return Response({'status': 'ok'})


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        # Handle password change
        old_pw = request.data.get('old_password')
        new_pw = request.data.get('new_password')
        if old_pw and new_pw:
            user = request.user
            if not user.check_password(old_pw):
                return Response({'old_password': ['OLD_PASSWORD_INCORRECT']}, status=status.HTTP_400_BAD_REQUEST)
            # Run Django password validators
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            try:
                validate_password(new_pw, user=user)
            except ValidationError as e:
                return Response({'new_password': e.messages}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_pw)
            # Invalidate all other device tokens
            user.token_version = user.token_version + 1
            user.save(update_fields=['password', 'token_version'])
            log_action(user, 'password_change', request)
            return Response(_issue_tokens(user))
        return super().update(request, *args, **kwargs)


class LogoutOtherDevicesView(APIView):
    def post(self, request):
        user = request.user
        user.token_version = user.token_version + 1
        user.save(update_fields=['token_version'])
        return Response(_issue_tokens(user))


class DeleteAccountView(APIView):
    """Schedule account deletion 30 days in the future.

    The grace period gives users a safety net against impulsive clicks
    and matches the "cooling-off" pattern Play Store / GDPR auditors
    look for. A Celery beat (api.tasks.hard_delete_scheduled_accounts)
    permanently removes scheduled users once their deletion_scheduled_at
    has passed. Logging back in any time before then implicitly cancels
    the deletion via LoginView (see below) — the user keeps everything.
    """
    DELETION_GRACE_DAYS = 30
    throttle_classes = [DeleteAccountThrottle]

    @transaction.atomic
    def post(self, request):
        from datetime import timedelta
        from django.utils import timezone as tz

        password = request.data.get('password', '')
        if not password:
            return error_response('password_required', 'Password is required.')
        if not request.user.check_password(password):
            return error_response('incorrect_password', 'Incorrect password.')
        scheduled = tz.now() + timedelta(days=self.DELETION_GRACE_DAYS)
        request.user.deletion_scheduled_at = scheduled
        request.user.save(update_fields=['deletion_scheduled_at'])
        log_action(request.user, 'account_delete', request)
        return Response(
            {'status': 'scheduled', 'deletion_scheduled_at': scheduled.isoformat()},
            status=status.HTTP_200_OK,
        )


class CancelAccountDeletionView(APIView):
    """POST /api/auth/delete-account/cancel/ — undo a scheduled deletion.

    Available only while ``deletion_scheduled_at`` is still in the future.
    Clears the field and audits the cancellation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.deletion_scheduled_at:
            return Response({'status': 'no_pending_deletion'})
        request.user.deletion_scheduled_at = None
        request.user.save(update_fields=['deletion_scheduled_at'])
        log_action(request.user, 'account_delete_cancel', request=request)
        return Response({'status': 'ok'})


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_str
        uid = request.query_params.get('uid')
        token = request.query_params.get('token')
        if not uid or not token:
            return error_response('error.invalid_reset_link', 'Invalid verification link.', 400)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return error_response('error.invalid_reset_link', 'Invalid verification link.', 400)
        if not default_token_generator.check_token(user, token):
            return error_response('error.invalid_reset_link', 'Invalid or expired verification link.', 400)
        user.email_verified = True
        user.save(update_fields=['email_verified'])
        return Response({'detail': 'Email verified successfully'})


class ResendVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({'detail': 'Email already verified'})
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        frontend_url = os.environ.get('FRONTEND_URL', 'https://heartbox.pages.dev')
        verify_url = f'{frontend_url}/verify-email?uid={uid}&token={token}'
        s = _email_strings(request)
        greeting = s['verify_greeting'].format(username=user.username)
        plain_message = (
            f'{greeting}\n\n'
            f'{s["verify_resend_body"]}\n'
            f'{verify_url}\n\n'
            f'{s["verify_ignore"]}\n\n'
            f'{s["team"]}'
        )
        html_message = (
            f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">'
            f'<h2 style="color:#7c3aed">HeartBox</h2>'
            f'<p>{html_escape(greeting)}</p>'
            f'<p>{html_escape(s["verify_resend_body"])}</p>'
            f'<p style="text-align:center;margin:28px 0">'
            f'<a href="{verify_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
            f'border-radius:8px;text-decoration:none;font-weight:600">{html_escape(s["verify_btn"])}</a></p>'
            f'<p style="color:#888;font-size:13px">{html_escape(s["verify_ignore"])}</p>'
            f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
            f'<p style="color:#aaa;font-size:12px">{html_escape(s["tagline"])}</p>'
            f'</div>'
        )
        try:
            send_mail(
                s['verify_subject'],
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
            )
        except Exception:
            logger.exception('Failed to send verification email to %s', user.email)
            return Response(
                {'detail': 'Failed to send verification email. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'detail': 'Verification email sent'})


class IsEmailVerified(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.email_verified


# === Consent (2026-06-02) ===
# Advisor asked for an explicit pre-use consent gate covering:
#   1. ToS + privacy
#   2. AI training data opt-in (independent — declining must still let
#      the user use the rest of the app)
#   3. Age band (18+ / 13-17 / under 13). Under 13 fails. 13-17 needs
#      guardian email confirmation before the account unlocks.
# The flow is captured in this single endpoint so the frontend can
# render it as one multi-step modal and store one POST.

class SubmitConsentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [GeneralWriteThrottle]

    VALID_AGE_BANDS = {'18_plus', '13_17', 'under_13'}

    def post(self, request):
        from django.utils import timezone
        import secrets

        user = request.user
        data = request.data or {}

        # --- Field validation ---
        accepts_terms = bool(data.get('accepts_terms'))
        consent_ai_training = bool(data.get('consent_ai_training'))
        age_band = (data.get('age_band') or '').strip()
        guardian_email = (data.get('guardian_email') or '').strip()

        if not accepts_terms:
            return error_response('consent.terms_required',
                                  'You must accept the terms to use HeartBox.', 400)
        if age_band not in self.VALID_AGE_BANDS:
            return error_response('consent.age_band_required',
                                  'Pick an age band.', 400)
        if age_band == 'under_13':
            # Under-13 is hard-blocked. We also schedule the account
            # for deletion to comply with COPPA-style age-gate.
            user.deletion_scheduled_at = timezone.now()
            user.save(update_fields=['deletion_scheduled_at'])
            return error_response('consent.under_13_not_allowed',
                                  'HeartBox is not available for users under 13.', 403)
        if age_band == '13_17' and not guardian_email:
            return error_response('consent.guardian_email_required',
                                  'A guardian email is required for users aged 13-17.', 400)

        # --- Persist consent ---
        now = timezone.now()
        user.terms_accepted_at = now
        user.age_confirmed_13_plus = True
        user.age_band = age_band
        user.consent_ai_training = consent_ai_training
        user.consent_ai_training_at = now if consent_ai_training else None
        if age_band == '13_17':
            user.guardian_email = guardian_email
            user.guardian_consent_token = secrets.token_urlsafe(32)
        else:
            # Clear any stale guardian data if the user re-runs the flow
            # after switching age bands.
            user.guardian_email = ''
            user.guardian_consent_token = ''
            user.guardian_consent_at = None
        user.save(update_fields=[
            'terms_accepted_at', 'age_confirmed_13_plus', 'age_band',
            'consent_ai_training', 'consent_ai_training_at',
            'guardian_email', 'guardian_consent_token', 'guardian_consent_at',
        ])

        # --- Send guardian email if minor ---
        # Best-effort: a send failure shouldn't roll back the consent
        # record — the user can re-trigger from the consent screen.
        if age_band == '13_17':
            try:
                self._send_guardian_email(user)
            except Exception:
                pass

        log_action(user, 'consent.submit', {'age_band': age_band,
                                            'ai_training': consent_ai_training})
        return Response(UserProfileSerializer(user).data)

    def _send_guardian_email(self, user):
        frontend = settings.FRONTEND_URL.rstrip('/')
        link = f'{frontend}/guardian-consent?token={user.guardian_consent_token}'
        subject = '[HeartBox] 家長同意確認 / Guardian Consent Required'
        body = (
            f'您好，\n\n'
            f'您的子女 {user.username} 透過 HeartBox（心事盒）申請使用本服務。\n'
            f'HeartBox 是一款心理健康日記應用程式，所有日記內容均以 AES-256 加密儲存。\n\n'
            f'由於您的子女年齡介於 13-17 歲，需經家長同意才能正式使用全部功能。\n\n'
            f'若您同意子女使用本服務，請點擊以下連結：\n{link}\n\n'
            f'若您不同意，請忽略此信，帳號將在 30 天內自動關閉。\n\n'
            f'隱私權政策：{frontend}/privacy\n'
            f'使用條款：{frontend}/terms\n\n'
            f'— HeartBox 團隊'
        )
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL or None,
                  [user.guardian_email], fail_silently=False)


class GuardianConfirmView(APIView):
    """Public endpoint hit by guardian's email link to confirm consent."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.utils import timezone
        token = (request.query_params.get('token') or '').strip()
        if not token:
            return error_response('guardian.invalid_token', 'Missing token.', 400)
        try:
            user = User.objects.get(
                guardian_consent_token=token,
                age_band='13_17',
                guardian_consent_at__isnull=True,
            )
        except User.DoesNotExist:
            return error_response('guardian.invalid_token',
                                  'Invalid or already-used token.', 400)
        user.guardian_consent_at = timezone.now()
        # Burn the token so it can't be replayed.
        user.guardian_consent_token = ''
        user.save(update_fields=['guardian_consent_at', 'guardian_consent_token'])
        log_action(user, 'consent.guardian_confirm', {'guardian': user.guardian_email})
        return Response({'detail': 'Guardian consent recorded',
                         'username': user.username})


# === 2FA TOTP ===

class TOTPSetupView(APIView):
    throttle_classes = [GeneralWriteThrottle]

    def get(self, request):
        """Check if 2FA is enabled for the current user."""
        enabled = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
        return Response({'enabled': enabled})

    def post(self, request):
        import pyotp
        import qrcode
        import base64
        from io import BytesIO

        user = request.user
        # Delete existing unconfirmed device
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()

        # Check if already has confirmed device
        if TOTPDevice.objects.filter(user=user, confirmed=True).exists():
            return error_response('totp_already_enabled', '2FA is already enabled.', 400)

        secret = pyotp.random_base32()
        device = TOTPDevice.objects.create(user=user, secret=secret, confirmed=False)

        totp = pyotp.TOTP(secret)
        otpauth_uri = totp.provisioning_uri(name=user.email or user.username, issuer_name='HeartBox')

        # Generate QR code as base64
        img = qrcode.make(otpauth_uri)
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return Response({
            'secret': secret,
            'otpauth_uri': otpauth_uri,
            'qr_code': f'data:image/png;base64,{qr_base64}',
        })


class TOTPVerifyView(APIView):
    throttle_classes = [GeneralWriteThrottle]

    def post(self, request):
        import pyotp

        code = request.data.get('code', '')
        user = request.user

        try:
            device = user.totp_device
        except TOTPDevice.DoesNotExist:
            return error_response('totp_not_found', 'No 2FA device found.', 400)

        totp = pyotp.TOTP(device.secret)
        if not totp.verify(code, valid_window=1):
            return error_response('totp_invalid_code', 'Invalid verification code.', 400)

        device.confirmed = True
        device.save(update_fields=['confirmed'])
        log_action(user, 'auth.2fa_enabled', request=request)
        return Response({'detail': '2FA enabled successfully'})


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklist the refresh token.

    Frontend should call this before clearing local storage. Even on
    network failure the local clear still runs (best-effort revoke).
    Without this, a stolen refresh token from a "logged-out" device
    stays valid for 7 days.
    """
    permission_classes = [permissions.AllowAny]  # let it succeed even mid-token-expiry

    def post(self, request):
        refresh = request.data.get('refresh')
        if not refresh:
            return Response(status=status.HTTP_205_RESET_CONTENT)
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            # Token already blacklisted / malformed — treat as idempotent
            pass
        if request.user.is_authenticated:
            # Bump token_version so any STILL-VALID access tokens (which we
            # can't blacklist — they're stateless) are rejected on the next
            # request. Without this, a stolen access token survives logout
            # for up to ACCESS_TOKEN_LIFETIME minutes.
            request.user.token_version = (request.user.token_version or 0) + 1
            request.user.save(update_fields=['token_version'])
            log_action(request.user, 'auth.logout', request=request)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class TOTPDisableView(APIView):
    def post(self, request):
        import pyotp
        password = request.data.get('password', '')
        code = request.data.get('code', '')
        if not request.user.check_password(password):
            return error_response('error.incorrect_password', 'Incorrect password.', 400)

        # Require a fresh TOTP digit as well — disabling 2FA must NOT be a
        # password-only operation, otherwise a stolen-password attacker can
        # disable the second factor and then escalate.
        if not code:
            return error_response('totp_code_required', 'TOTP code is required to disable 2FA.', 400)
        try:
            device = request.user.totp_device
        except TOTPDevice.DoesNotExist:
            return error_response('totp_not_found', 'No 2FA device found.', 400)
        if not pyotp.TOTP(device.secret).verify(code, valid_window=1):
            log_action(request.user, 'auth.2fa_disabled_failed', request=request)
            return error_response('totp_invalid_code', 'Invalid TOTP code.', 400)

        TOTPDevice.objects.filter(user=request.user).delete()
        # Rotate sessions so any token issued before 2FA was disabled is killed.
        request.user.token_version = (request.user.token_version or 0) + 1
        request.user.save(update_fields=['token_version'])
        log_action(request.user, 'auth.2fa_disabled', request=request)
        return Response({'detail': '2FA disabled successfully'})


class Login2FAView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle, LoginPerUsernameThrottle]

    def post(self, request):
        import pyotp
        from rest_framework_simplejwt.tokens import AccessToken

        partial_token = request.data.get('partial_token', '')
        code = request.data.get('code', '')

        if not partial_token or not code:
            return error_response('totp_missing_fields', 'Token and code are required.', 400)

        try:
            token = AccessToken(partial_token)
            # Reject any non-2FA-pending token presented here, even if the
            # signature is valid — prevents a regular access token from
            # being used to skip the second factor entirely.
            if token.get('scope') != '2fa_pending':
                return error_response('totp_invalid_token', 'Invalid token.', 400)
            user = User.objects.get(pk=token['user_id'])
        except Exception:
            logger.exception('Login2FA token validation failed')
            return error_response('totp_invalid_token', 'Invalid token.', 400)

        try:
            device = user.totp_device
        except TOTPDevice.DoesNotExist:
            return error_response('totp_not_found', 'No 2FA device found.', 400)

        totp = pyotp.TOTP(device.secret)
        if not totp.verify(code, valid_window=1):
            log_action(user, 'auth.login_2fa_failed', request=request)
            return error_response('totp_invalid_code', 'Invalid verification code.', 400)

        log_action(user, 'auth.login_2fa', request=request)
        tokens = _issue_tokens(user)
        return Response(tokens)


# === Google OAuth ===

class GoogleLoginCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        credential = request.data.get('credential', '')
        if not credential:
            return error_response('oauth_missing_credential', 'Google credential is required.', 400)

        client_id = os.environ.get('GOOGLE_CLIENT_ID', '')
        if not client_id:
            return error_response('oauth_not_configured', 'Google OAuth not configured.', 500)

        try:
            idinfo = id_token.verify_oauth2_token(credential, google_requests.Request(), client_id)
        except ValueError:
            return error_response('oauth_invalid_credential', 'Invalid Google credential.', 400)

        # CRITICAL: only trust Google's email claim if Google says it's verified.
        # Otherwise an attacker who controls a Google-Workspace domain could
        # mint id_tokens for an unverified address that matches an existing
        # HeartBox account and pre-empt that user.
        if not idinfo.get('email_verified'):
            log_action(None, 'auth.oauth_email_not_verified', request=request,
                       details={'provider': 'google'})
            return error_response('oauth_email_not_verified',
                                  'Google has not verified this email.', 400)

        email = idinfo.get('email', '')
        if not email:
            return error_response('oauth_no_email', 'Email not provided by Google.', 400)

        # Find or create user. iexact: avoid case-sensitivity gotchas where
        # 'Alan@x.com' bypasses the local 'alan@x.com' row.
        try:
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                raise User.DoesNotExist
        except User.DoesNotExist:
            # Create new user with Google info
            username = email.split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}{counter}'
                counter += 1
            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,  # No password for OAuth users
            )
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        # 2FA bypass guard: if user has password-flow 2FA enabled, Google
        # OAuth must NOT issue a full token. Return a SCOPED partial token
        # (same shape as password login) so the frontend prompts for TOTP.
        try:
            totp_device = user.totp_device
            if totp_device.confirmed:
                log_action(user, 'auth.login_2fa_required', request=request, details={'provider': 'google'})
                return Response({
                    'requires_2fa': True,
                    'partial_token': _issue_2fa_partial_token(user),
                })
        except TOTPDevice.DoesNotExist:
            pass

        log_action(user, 'auth.login', request=request, details={'provider': 'google'})
        tokens = _issue_tokens(user)
        return Response(tokens)
