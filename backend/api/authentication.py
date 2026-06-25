from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication


class VersionedJWTAuthentication(JWTAuthentication):
    """JWT authentication that invalidates tokens when user token_version changes."""

    def get_user(self, validated_token):
        # Refuse scoped partial tokens (e.g. 2fa_pending) from authenticating
        # regular API endpoints. Login2FAView is the only consumer of the
        # 2fa_pending scope and it bypasses this auth class entirely.
        scope = validated_token.get('scope')
        if scope:
            raise exceptions.AuthenticationFailed(
                f'Scoped token (scope={scope}) cannot be used for general auth',
                code='token_not_valid',
            )
        user = super().get_user(validated_token)
        token_version = validated_token.get('token_version')
        if token_version is None:
            raise exceptions.AuthenticationFailed('Token is no longer valid', code='token_not_valid')
        if int(token_version) != int(getattr(user, 'token_version', 0)):
            raise exceptions.AuthenticationFailed('Token is no longer valid', code='token_not_valid')
        return user


class VersionedJWTScheme(SimpleJWTScheme):
    """drf_spectacular extension so the OpenAPI schema documents this auth class as Bearer JWT."""
    target_class = 'api.authentication.VersionedJWTAuthentication'
    name = 'jwtAuth'
