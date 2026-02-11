from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.tokens import default_token_generator

from .models import CustomUser


class AuthSecurityTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='InitialPass123!',
        )

    def login(self, password='InitialPass123!'):
        resp = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': password,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data['access'], resp.data['refresh']

    def test_logout_other_devices_invalidates_old_tokens(self):
        old_access, _ = self.login()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {old_access}')
        profile_resp = self.client.get('/api/auth/profile/')
        self.assertEqual(profile_resp.status_code, status.HTTP_200_OK)

        logout_resp = self.client.post('/api/auth/logout-other-devices/')
        self.assertEqual(logout_resp.status_code, status.HTTP_200_OK)
        new_access = logout_resp.data['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {old_access}')
        old_profile_resp = self.client.get('/api/auth/profile/')
        self.assertEqual(old_profile_resp.status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        new_profile_resp = self.client.get('/api/auth/profile/')
        self.assertEqual(new_profile_resp.status_code, status.HTTP_200_OK)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_password_reset_flow(self):
        forgot_resp = self.client.post('/api/auth/password/forgot/', {
            'email': 'alice@example.com',
        }, format='json')
        self.assertEqual(forgot_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        reset_resp = self.client.post('/api/auth/password/reset/', {
            'uid': uid,
            'token': token,
            'new_password': 'UpdatedPass456!',
        }, format='json')
        self.assertEqual(reset_resp.status_code, status.HTTP_200_OK)

        login_resp = self.client.post('/api/auth/login/', {
            'username': 'alice',
            'password': 'UpdatedPass456!',
        }, format='json')
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

    def test_refresh_rejected_after_token_version_rotates(self):
        _, refresh = self.login()

        self.user.token_version += 1
        self.user.save(update_fields=['token_version'])

        refresh_resp = self.client.post('/api/auth/refresh/', {'refresh': refresh}, format='json')
        self.assertEqual(refresh_resp.status_code, status.HTTP_403_FORBIDDEN)
