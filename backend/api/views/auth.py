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
    DeleteAccountThrottle, GeneralWriteThrottle, LoginRateThrottle,
    PasswordResetRateThrottle, RefreshTokenThrottle, RegisterRateThrottle,
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
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterRateThrottle]

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
            html_message = (
                f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px">'
                f'<h2 style="color:#7c3aed">HeartBox</h2>'
                f'<p>{greeting}</p>'
                f'<p>{s["verify_register_body"]}</p>'
                f'<p style="text-align:center;margin:28px 0">'
                f'<a href="{verify_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
                f'border-radius:8px;text-decoration:none;font-weight:600">{s["verify_btn"]}</a></p>'
                f'<p style="color:#888;font-size:13px">{s["verify_ignore"]}</p>'
                f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
                f'<p style="color:#aaa;font-size:12px">{s["tagline"]}</p>'
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
        return super().validate(attrs)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = VersionedTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        # Check for 2FA
        try:
            totp_device = user.totp_device
            if totp_device.confirmed:
                # Return partial token indicating 2FA is needed
                partial_token = str(RefreshToken.for_user(user).access_token)
                return Response({
                    'requires_2fa': True,
                    'partial_token': partial_token,
                })
        except TOTPDevice.DoesNotExist:
            pass
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
                f'<p>{greeting}</p>'
                f'<p>{s["reset_html_body"]}</p>'
                f'<p style="text-align:center;margin:28px 0">'
                f'<a href="{reset_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
                f'border-radius:8px;text-decoration:none;font-weight:600">{s["reset_btn"]}</a></p>'
                f'<p style="color:#888;font-size:13px">{s["reset_expire"]} '
                f'{s["reset_ignore"]}</p>'
                f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
                f'<p style="color:#aaa;font-size:12px">{s["tagline"]}</p>'
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

    def post(self, request):
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
        # Run Django password validators
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({'detail': e.messages}, status=status.HTTP_400_BAD_REQUEST)
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
    """Permanently delete user account and all related data."""
    throttle_classes = [DeleteAccountThrottle]

    @transaction.atomic
    def post(self, request):
        password = request.data.get('password', '')
        if not password:
            return error_response('password_required', 'Password is required.')
        if not request.user.check_password(password):
            return error_response('incorrect_password', 'Incorrect password.')
        log_action(request.user, 'account_delete', request)
        request.user.delete()
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


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
            f'<p>{greeting}</p>'
            f'<p>{s["verify_resend_body"]}</p>'
            f'<p style="text-align:center;margin:28px 0">'
            f'<a href="{verify_url}" style="background:#7c3aed;color:#fff;padding:12px 32px;'
            f'border-radius:8px;text-decoration:none;font-weight:600">{s["verify_btn"]}</a></p>'
            f'<p style="color:#888;font-size:13px">{s["verify_ignore"]}</p>'
            f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
            f'<p style="color:#aaa;font-size:12px">{s["tagline"]}</p>'
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
        return Response({'detail': '2FA enabled successfully'})


class TOTPDisableView(APIView):
    def post(self, request):
        password = request.data.get('password', '')
        if not request.user.check_password(password):
            return error_response('error.incorrect_password', 'Incorrect password.', 400)

        TOTPDevice.objects.filter(user=request.user).delete()
        return Response({'detail': '2FA disabled successfully'})


class Login2FAView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        import pyotp
        from rest_framework_simplejwt.tokens import AccessToken

        partial_token = request.data.get('partial_token', '')
        code = request.data.get('code', '')

        if not partial_token or not code:
            return error_response('totp_missing_fields', 'Token and code are required.', 400)

        try:
            token = AccessToken(partial_token)
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
            return error_response('totp_invalid_code', 'Invalid verification code.', 400)

        tokens = _issue_tokens(user)
        return Response(tokens)


# === Google OAuth ===

class GoogleLoginCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

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

        email = idinfo.get('email', '')
        if not email:
            return error_response('oauth_no_email', 'Email not provided by Google.', 400)

        # Find or create user
        try:
            user = User.objects.filter(email=email).first()
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

        tokens = _issue_tokens(user)
        return Response(tokens)
