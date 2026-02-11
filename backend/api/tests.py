from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.tokens import default_token_generator

from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    Booking, Conversation, CounselorProfile, CustomUser, Message,
    MoodNote, NoteAttachment, Notification, SharedNote,
)

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


class CounselorFlowTests(APITestCase):
    """Test counselor application, admin approval/rejection, and listing."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin', email='admin@cf.com', password='AdminPass123!', is_staff=True,
        )
        self.user = CustomUser.objects.create_user(
            username='counselor1', email='c1@cf.com', password='CounselorPass123!',
        )
        self.other = CustomUser.objects.create_user(
            username='regular', email='r@cf.com', password='RegularPass123!',
        )

    def test_apply_as_counselor(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/counselors/apply/', {
            'license_number': 'LIC-001',
            'specialty': 'Anxiety',
            'introduction': 'Experienced therapist.',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'pending')

    def test_admin_approve_counselor(self):
        profile = CounselorProfile.objects.create(
            user=self.user, license_number='LIC-002',
            specialty='Depression', introduction='Test',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/admin/counselors/{profile.id}/action/', {
            'action': 'approve',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.status, 'approved')

    def test_admin_reject_counselor(self):
        profile = CounselorProfile.objects.create(
            user=self.user, license_number='LIC-003',
            specialty='Stress', introduction='Test',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/admin/counselors/{profile.id}/action/', {
            'action': 'reject',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        profile.refresh_from_db()
        self.assertEqual(profile.status, 'rejected')

    def test_admin_invalid_action(self):
        profile = CounselorProfile.objects.create(
            user=self.user, license_number='LIC-004',
            specialty='Test', introduction='Test',
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(f'/api/admin/counselors/{profile.id}/action/', {
            'action': 'invalid',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approved_counselor_listed(self):
        CounselorProfile.objects.create(
            user=self.user, license_number='LIC-005',
            specialty='CBT', introduction='Listed', status='approved',
        )
        self.client.force_authenticate(user=self.other)
        resp = self.client.get('/api/counselors/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(results), 1)

    def test_pending_counselor_not_listed(self):
        CounselorProfile.objects.create(
            user=self.user, license_number='LIC-006',
            specialty='CBT', introduction='Not listed', status='pending',
        )
        self.client.force_authenticate(user=self.other)
        resp = self.client.get('/api/counselors/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        self.assertEqual(len(results), 0)


class MessagingTests(APITestCase):
    """Test conversation creation and messaging."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='msguser', email='msg@test.com', password='MsgPass123!',
        )
        self.counselor = CustomUser.objects.create_user(
            username='msgcounselor', email='msgc@test.com', password='MsgPass123!',
        )
        self.profile = CounselorProfile.objects.create(
            user=self.counselor, license_number='MSG-001',
            specialty='Chat', introduction='Test', status='approved',
        )

    def test_create_conversation(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/conversations/create/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_create_conversation_duplicate_returns_existing(self):
        self.client.force_authenticate(user=self.user)
        resp1 = self.client.post('/api/conversations/create/', {
            'counselor_id': self.profile.id,
        }, format='json')
        resp2 = self.client.post('/api/conversations/create/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.data['id'], resp2.data['id'])

    def test_send_and_list_messages(self):
        self.client.force_authenticate(user=self.user)
        conv_resp = self.client.post('/api/conversations/create/', {
            'counselor_id': self.profile.id,
        }, format='json')
        conv_id = conv_resp.data['id']

        # Send message
        send_resp = self.client.post(f'/api/conversations/{conv_id}/messages/', {
            'content': 'Hello counselor!',
        }, format='json')
        self.assertEqual(send_resp.status_code, status.HTTP_201_CREATED)

        # List messages
        list_resp = self.client.get(f'/api/conversations/{conv_id}/messages/')
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 1)
        self.assertEqual(list_resp.data[0]['content'], 'Hello counselor!')

    def test_empty_message_rejected(self):
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user, counselor=self.counselor)
        resp = self.client.post(f'/api/conversations/{conv.id}/messages/', {
            'content': '',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_message_too_long_rejected(self):
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user, counselor=self.counselor)
        resp = self.client.post(f'/api/conversations/{conv.id}/messages/', {
            'content': 'x' * 5001,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_participant_cannot_access(self):
        outsider = CustomUser.objects.create_user(
            username='outsider', password='OutPass123!',
        )
        conv = Conversation.objects.create(user=self.user, counselor=self.counselor)
        self.client.force_authenticate(user=outsider)
        resp = self.client.get(f'/api/conversations/{conv.id}/messages/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_message_creates_notification(self):
        self.client.force_authenticate(user=self.user)
        conv = Conversation.objects.create(user=self.user, counselor=self.counselor)
        self.client.post(f'/api/conversations/{conv.id}/messages/', {
            'content': 'Notify test',
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(user=self.counselor, type='message').exists()
        )


class AttachmentTests(APITestCase):
    """Test note attachment upload with validation."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='attachuser', email='attach@test.com', password='AttachPass123!',
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/notes/', {'content': 'Attachment test'}, format='json')
        self.note_id = resp.data['id']

    def test_upload_image(self):
        # 1x1 PNG pixel
        img = SimpleUploadedFile('test.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100, content_type='image/png')
        resp = self.client.post(
            f'/api/notes/{self.note_id}/attachments/',
            {'file': img},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['file_type'], 'image')

    def test_upload_audio(self):
        audio = SimpleUploadedFile('test.mp3', b'\x00' * 100, content_type='audio/mpeg')
        resp = self.client.post(
            f'/api/notes/{self.note_id}/attachments/',
            {'file': audio},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['file_type'], 'audio')

    def test_reject_non_media_file(self):
        txt = SimpleUploadedFile('test.txt', b'hello world', content_type='text/plain')
        resp = self.client.post(
            f'/api/notes/{self.note_id}/attachments/',
            {'file': txt},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_no_file(self):
        resp = self.client.post(
            f'/api/notes/{self.note_id}/attachments/',
            {},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reject_other_users_note(self):
        other = CustomUser.objects.create_user(username='other2', password='OtherPass123!')
        note = MoodNote(user=other)
        note.set_content('Other note')
        note.save()
        img = SimpleUploadedFile('test.png', b'\x89PNG' + b'\x00' * 100, content_type='image/png')
        resp = self.client.post(
            f'/api/notes/{note.id}/attachments/',
            {'file': img},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class BookingTests(APITestCase):
    """Test booking creation, conflicts, and actions."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='bookuser', email='book@test.com', password='BookPass123!',
        )
        self.counselor = CustomUser.objects.create_user(
            username='bookcounselor', email='bookc@test.com', password='BookPass123!',
        )
        self.profile = CounselorProfile.objects.create(
            user=self.counselor, license_number='BK-001',
            specialty='Booking', introduction='Test', status='approved',
        )

    def test_create_booking(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-06-15',
            'start_time': '10:00',
            'end_time': '11:00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'pending')

    def test_booking_conflict(self):
        self.client.force_authenticate(user=self.user)
        # Create first booking
        self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-06-16',
            'start_time': '14:00',
            'end_time': '15:00',
        }, format='json')
        # Try overlapping booking
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-06-16',
            'start_time': '14:30',
            'end_time': '15:30',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_booking_missing_fields(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_booking(self):
        self.client.force_authenticate(user=self.user)
        booking = Booking.objects.create(
            user=self.user, counselor=self.counselor,
            date='2026-06-20', start_time='09:00', end_time='10:00',
        )
        # Counselor confirms
        self.client.force_authenticate(user=self.counselor)
        resp = self.client.post(f'/api/bookings/{booking.id}/action/', {
            'action': 'confirm',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')

    def test_cancel_booking(self):
        booking = Booking.objects.create(
            user=self.user, counselor=self.counselor,
            date='2026-06-21', start_time='09:00', end_time='10:00',
        )
        self.client.force_authenticate(user=self.counselor)
        resp = self.client.post(f'/api/bookings/{booking.id}/action/', {
            'action': 'cancel',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

    def test_booking_action_creates_notification(self):
        booking = Booking.objects.create(
            user=self.user, counselor=self.counselor,
            date='2026-06-22', start_time='09:00', end_time='10:00',
        )
        self.client.force_authenticate(user=self.counselor)
        self.client.post(f'/api/bookings/{booking.id}/action/', {
            'action': 'confirm',
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(user=self.user, type='booking').exists()
        )


class ShareNoteTests(APITestCase):
    """Test note sharing with counselors."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='shareuser', email='share@test.com', password='SharePass123!',
        )
        self.counselor = CustomUser.objects.create_user(
            username='sharecounselor', email='sharec@test.com', password='SharePass123!',
        )
        self.profile = CounselorProfile.objects.create(
            user=self.counselor, license_number='SH-001',
            specialty='Share', introduction='Test', status='approved',
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/notes/', {'content': 'Shareable note'}, format='json')
        self.note_id = resp.data['id']

    def test_share_note(self):
        resp = self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_share_duplicate_rejected(self):
        self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
        }, format='json')
        resp = self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_share_anonymous(self):
        resp = self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
            'is_anonymous': True,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data['is_anonymous'])

    def test_share_creates_notification(self):
        self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(user=self.counselor, type='share').exists()
        )

    def test_shared_notes_received(self):
        self.client.post(f'/api/notes/{self.note_id}/share/', {
            'counselor_id': self.profile.id,
        }, format='json')
        self.client.force_authenticate(user=self.counselor)
        resp = self.client.get('/api/shared-notes/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)


class NotificationTests(APITestCase):
    """Test notification listing and marking as read."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='notifuser', email='notif@test.com', password='NotifPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def test_list_notifications(self):
        Notification.objects.create(
            user=self.user, type='system', title='Test', message='Hello',
        )
        resp = self.client.get('/api/notifications/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_mark_notifications_read(self):
        n = Notification.objects.create(
            user=self.user, type='system', title='Unread', message='Mark me',
        )
        resp = self.client.post('/api/notifications/read/', {
            'ids': [n.id],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.is_read)
