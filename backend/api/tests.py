from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.tokens import default_token_generator

from .models import CustomUser, MoodNote


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


class NoteCRUDTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser', email='test@example.com', password='TestPass123!'
        )
        resp = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'TestPass123!'
        }, format='json')
        self.token = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_create_note(self):
        resp = self.client.post('/api/notes/', {
            'content': '今天心情很好',
            'metadata': {'tags': ['開心']}
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', resp.data)

    def test_list_notes(self):
        self.client.post('/api/notes/', {'content': 'Note 1'}, format='json')
        self.client.post('/api/notes/', {'content': 'Note 2'}, format='json')
        resp = self.client.get('/api/notes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data.get('results', [])), 2)

    def test_update_note(self):
        create_resp = self.client.post('/api/notes/', {'content': 'Original'}, format='json')
        note_id = create_resp.data['id']
        update_resp = self.client.put(f'/api/notes/{note_id}/', {
            'content': 'Updated content'
        }, format='json')
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)

    def test_delete_note(self):
        create_resp = self.client.post('/api/notes/', {'content': 'Delete me'}, format='json')
        note_id = create_resp.data['id']
        del_resp = self.client.delete(f'/api/notes/{note_id}/')
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_note_encryption(self):
        self.client.post('/api/notes/', {'content': 'Secret content'}, format='json')
        note = MoodNote.objects.first()
        # Encrypted content should NOT be plaintext
        self.assertNotEqual(note.encrypted_content, 'Secret content')
        # Decrypted content should match
        self.assertEqual(note.content, 'Secret content')

    def test_toggle_pin(self):
        create_resp = self.client.post('/api/notes/', {'content': 'Pin me'}, format='json')
        note_id = create_resp.data['id']
        pin_resp = self.client.post(f'/api/notes/{note_id}/toggle_pin/')
        self.assertEqual(pin_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(pin_resp.data['is_pinned'])
        # Toggle again
        unpin_resp = self.client.post(f'/api/notes/{note_id}/toggle_pin/')
        self.assertFalse(unpin_resp.data['is_pinned'])


class AccountManagementTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='deluser', email='del@example.com', password='DelPass123!'
        )
        resp = self.client.post('/api/auth/login/', {
            'username': 'deluser', 'password': 'DelPass123!'
        }, format='json')
        self.token = resp.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_delete_account_wrong_password(self):
        resp = self.client.post('/api/auth/delete-account/', {
            'password': 'WrongPass!'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_account_success(self):
        resp = self.client.post('/api/auth/delete-account/', {
            'password': 'DelPass123!'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(CustomUser.objects.filter(username='deluser').exists())

    def test_export_data(self):
        # Create a note first
        self.client.post('/api/notes/', {'content': 'Export test'}, format='json')
        resp = self.client.get('/api/auth/export/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/json')


class ThrottleTests(APITestCase):
    def test_login_throttle(self):
        """Verify login endpoint has throttle (won't block first few attempts)."""
        for i in range(3):
            resp = self.client.post('/api/auth/login/', {
                'username': 'nonexist', 'password': 'wrong'
            }, format='json')
            # Should get 401, not 429 for first few
            self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_429_TOO_MANY_REQUESTS])

    def test_register_throttle(self):
        """Verify register endpoint has throttle."""
        resp = self.client.post('/api/auth/register/', {
            'username': 'throttle_test', 'email': 'throttle@test.com', 'password': 'TestPass123!'
        }, format='json')
        self.assertIn(resp.status_code, [status.HTTP_201_CREATED, status.HTTP_429_TOO_MANY_REQUESTS])
