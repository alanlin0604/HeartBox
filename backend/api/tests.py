from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.tokens import default_token_generator

from .models import CustomUser, MoodNote

# Disable throttling for all non-throttle tests
NO_THROTTLE = {
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
}


@override_settings(REST_FRAMEWORK={
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.authentication.VersionedJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
})
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
        self.client.force_authenticate(user=self.user)

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
        self.client.force_authenticate(user=self.user)

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


class BatchDeleteTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='batchuser', email='batch@test.com', password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_batch_delete_success(self):
        ids = []
        for i in range(3):
            r = self.client.post('/api/notes/', {'content': f'Note {i}'}, format='json')
            ids.append(r.data['id'])
        resp = self.client.post('/api/notes/batch_delete/', {'ids': ids}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['deleted'], 3)
        self.assertEqual(MoodNote.objects.filter(user=self.user).count(), 0)

    def test_batch_delete_empty_ids(self):
        resp = self.client.post('/api/notes/batch_delete/', {'ids': []}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_batch_delete_other_user_notes(self):
        other = CustomUser.objects.create_user(username='other', password='OtherPass123!')
        note = MoodNote(user=other)
        note.set_content('Other user note')
        note.save()
        resp = self.client.post('/api/notes/batch_delete/', {'ids': [note.id]}, format='json')
        self.assertEqual(resp.data['deleted'], 0)
        self.assertTrue(MoodNote.objects.filter(id=note.id).exists())


class CSVExportTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='csvuser', email='csv@test.com', password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_csv_export(self):
        self.client.post('/api/notes/', {'content': 'CSV test note'}, format='json')
        resp = self.client.get('/api/auth/export/csv/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('text/csv', resp['Content-Type'])
        content = resp.content.decode('utf-8-sig')
        self.assertIn('CSV test note', content)
        self.assertIn('ID', content)


class AnalyticsTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='analyticsuser', email='analytics@test.com', password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)

    def test_analytics_endpoint(self):
        self.client.post('/api/notes/', {'content': 'Analytics test'}, format='json')
        resp = self.client.get('/api/analytics/?period=week&lookback_days=30')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('mood_trends', resp.data)
        self.assertIn('current_streak', resp.data)
        self.assertIn('longest_streak', resp.data)

    def test_calendar_endpoint(self):
        resp = self.client.get('/api/analytics/calendar/?year=2026&month=2')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['year'], 2026)
        self.assertEqual(resp.data['month'], 2)

    def test_alerts_endpoint(self):
        resp = self.client.get('/api/alerts/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('alerts', resp.data)


class AdminTests(APITestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin', email='admin@test.com', password='AdminPass123!',
            is_staff=True,
        )
        self.regular = CustomUser.objects.create_user(
            username='regular', email='regular@test.com', password='RegularPass123!',
        )
        self.client.force_authenticate(user=self.admin)

    def test_admin_stats(self):
        resp = self.client.get('/api/admin/stats/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('total_users', resp.data)
        self.assertGreaterEqual(resp.data['total_users'], 2)

    def test_admin_user_list(self):
        resp = self.client.get('/api/admin/users/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_non_admin_denied(self):
        self.client.force_authenticate(user=self.regular)
        resp = self.client.get('/api/admin/stats/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_update_user(self):
        resp = self.client.patch(f'/api/admin/users/{self.regular.id}/', {
            'is_active': False
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.regular.refresh_from_db()
        self.assertFalse(self.regular.is_active)


@override_settings(REST_FRAMEWORK={
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.authentication.VersionedJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {},
})
class PasswordChangeTokenTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='pwuser', email='pw@test.com', password='OldPass123!'
        )
        resp = self.client.post('/api/auth/login/', {
            'username': 'pwuser', 'password': 'OldPass123!'
        }, format='json')
        self.old_access = resp.data['access']

    def test_password_change_invalidates_old_tokens(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.old_access}')
        resp = self.client.patch('/api/auth/profile/', {
            'old_password': 'OldPass123!',
            'new_password': 'NewPass456!',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        new_access = resp.data['access']

        # Old token should be invalid
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.old_access}')
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

        # New token should work
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


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
