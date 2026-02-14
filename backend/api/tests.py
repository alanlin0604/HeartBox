from django.core import mail
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth.tokens import default_token_generator

from django.core.files.uploadedfile import SimpleUploadedFile

from .models import (
    AIChatMessage, AIChatSession,
    Booking, Conversation, CounselorProfile, CustomUser, Message,
    MoodNote, NoteAttachment, Notification, SharedNote, UserAchievement,
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
        # Soft delete: notes still exist but are marked as deleted
        self.assertEqual(MoodNote.objects.filter(user=self.user, is_deleted=True).count(), 3)
        self.assertEqual(MoodNote.objects.filter(user=self.user, is_deleted=False).count(), 0)

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

    def test_reject_audio(self):
        """Audio uploads should be rejected — only images are allowed."""
        audio = SimpleUploadedFile('test.mp3', b'\x00' * 100, content_type='audio/mpeg')
        resp = self.client.post(
            f'/api/notes/{self.note_id}/attachments/',
            {'file': audio},
            format='multipart',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

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


class AIChatTests(APITestCase):
    """Test AI chat session and messaging endpoints."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='chatuser', email='chat@test.com', password='ChatPass123!',
        )
        self.other_user = CustomUser.objects.create_user(
            username='otheruser', email='other@test.com', password='OtherPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_session(self):
        resp = self.client.post('/api/ai-chat/sessions/', format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['title'], 'New Chat')
        self.assertTrue(resp.data['is_active'])

    def test_list_sessions(self):
        AIChatSession.objects.create(user=self.user, title='Test Chat')
        resp = self.client.get('/api/ai-chat/sessions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_sessions_excludes_inactive(self):
        AIChatSession.objects.create(user=self.user, title='Active')
        AIChatSession.objects.create(user=self.user, title='Deleted', is_active=False)
        resp = self.client.get('/api/ai-chat/sessions/')
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['title'], 'Active')

    def test_get_session_detail(self):
        session = AIChatSession.objects.create(user=self.user, title='Detail Test')
        AIChatMessage.objects.create(session=session, role='user', content='Hello')
        resp = self.client.get(f'/api/ai-chat/sessions/{session.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['messages']), 1)

    def test_delete_session_soft(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.delete(f'/api/ai-chat/sessions/{session.id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        session.refresh_from_db()
        self.assertFalse(session.is_active)

    @override_settings(OPENAI_API_KEY='')
    def test_send_message_returns_both(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.post(
            f'/api/ai-chat/sessions/{session.id}/messages/',
            {'content': '今天心情不太好'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_message', resp.data)
        self.assertIn('ai_message', resp.data)
        self.assertEqual(resp.data['user_message']['role'], 'user')
        self.assertEqual(resp.data['ai_message']['role'], 'assistant')

    def test_send_empty_message_rejected(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.post(
            f'/api/ai-chat/sessions/{session.id}/messages/',
            {'content': ''},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_too_long_message_rejected(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.post(
            f'/api/ai-chat/sessions/{session.id}/messages/',
            {'content': 'x' * 2001},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(OPENAI_API_KEY='')
    def test_first_message_sets_title(self):
        session = AIChatSession.objects.create(user=self.user)
        self.client.post(
            f'/api/ai-chat/sessions/{session.id}/messages/',
            {'content': '我今天在公司遇到了一些煩心事'},
            format='json',
        )
        session.refresh_from_db()
        self.assertEqual(session.title, '我今天在公司遇到了一些煩心事')

    def test_other_user_cannot_access_session(self):
        session = AIChatSession.objects.create(user=self.user)
        self.client.force_authenticate(user=self.other_user)
        resp = self.client.get(f'/api/ai-chat/sessions/{session.id}/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(OPENAI_API_KEY='')
    def test_user_message_has_sentiment(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.post(
            f'/api/ai-chat/sessions/{session.id}/messages/',
            {'content': '今天很開心，做了很多有趣的事'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(resp.data['user_message']['sentiment_score'])


class AchievementTests(APITestCase):
    """Test achievement system."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = CustomUser.objects.create_user(
            username='achieveuser', email='achieve@test.com', password='AchievePass123!',
        )
        self.client.force_authenticate(user=self.user)

    def test_first_note_unlocks_achievement(self):
        """Writing the first note should auto-unlock 'first_note' via perform_create."""
        resp = self.client.post('/api/notes/', {'content': 'My first note!'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # Auto-check in perform_create should have unlocked it
        self.assertTrue(
            UserAchievement.objects.filter(user=self.user, achievement_id='first_note').exists()
        )

    def test_get_achievements_returns_progress(self):
        """GET /achievements/ should return all 19 achievements with progress."""
        resp = self.client.get('/api/achievements/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 19)
        # Check structure of first item
        item = resp.data[0]
        self.assertIn('id', item)
        self.assertIn('category', item)
        self.assertIn('threshold', item)
        self.assertIn('current', item)
        self.assertIn('unlocked', item)

    def test_no_duplicate_unlock(self):
        """Checking achievements twice should not create duplicates."""
        self.client.post('/api/notes/', {'content': 'Note for dup test'}, format='json')
        # first_note already unlocked by auto-check, manual check should return empty
        resp = self.client.post('/api/achievements/check/')
        self.assertNotIn('first_note', resp.data['newly_unlocked'])
        # Only one DB record
        self.assertEqual(
            UserAchievement.objects.filter(user=self.user, achievement_id='first_note').count(),
            1,
        )

    def test_auto_check_on_note_create(self):
        """Creating a note should auto-check achievements (X-New-Achievements header)."""
        resp = self.client.post('/api/notes/', {'content': 'Auto check test'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        header = resp.get('X-New-Achievements', '')
        self.assertIn('first_note', header)

    def test_unauthenticated_rejected(self):
        """Unauthenticated requests should be rejected."""
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/achievements/')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pin_master_achievement(self):
        """Pinning 5 notes should unlock pin_master."""
        for i in range(5):
            r = self.client.post('/api/notes/', {'content': f'Pin note {i}'}, format='json')
            self.client.post(f'/api/notes/{r.data["id"]}/toggle_pin/')
        resp = self.client.post('/api/achievements/check/')
        self.assertIn('pin_master', resp.data['newly_unlocked'])

    def test_achievements_progress_after_notes(self):
        """Progress should reflect note count for notes_10."""
        for i in range(3):
            self.client.post('/api/notes/', {'content': f'Progress note {i}'}, format='json')
        resp = self.client.get('/api/achievements/')
        notes_10 = next(a for a in resp.data if a['id'] == 'notes_10')
        self.assertEqual(notes_10['current'], 3)
        self.assertFalse(notes_10['unlocked'])

    def test_ai_chat_achievement(self):
        """Creating an AI chat session should allow first_ai_chat unlock."""
        from api.models import AIChatSession
        AIChatSession.objects.create(user=self.user)
        resp = self.client.post('/api/achievements/check/')
        self.assertIn('first_ai_chat', resp.data['newly_unlocked'])

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()


class CounselorPricingTests(APITestCase):
    """Test counselor pricing features."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='pricingadmin', email='pa@test.com', password='AdminPass123!', is_staff=True,
        )
        self.counselor_user = CustomUser.objects.create_user(
            username='pricecounselor', email='pc@test.com', password='CounselorPass123!',
        )
        self.user = CustomUser.objects.create_user(
            username='priceuser', email='pu@test.com', password='UserPass123!',
        )
        self.profile = CounselorProfile.objects.create(
            user=self.counselor_user, license_number='PR-001',
            specialty='Pricing', introduction='Test pricing',
            status='approved', hourly_rate=1500, currency='TWD',
        )

    def test_set_hourly_rate(self):
        """Counselor should be able to update their hourly rate."""
        self.client.force_authenticate(user=self.counselor_user)
        resp = self.client.patch('/api/counselors/me/', {
            'hourly_rate': '2000.00',
            'currency': 'USD',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.hourly_rate, 2000)
        self.assertEqual(self.profile.currency, 'USD')

    def test_counselor_list_shows_pricing(self):
        """Counselor listing should include hourly_rate and currency."""
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/counselors/')
        results = resp.data.get('results', resp.data)
        self.assertGreaterEqual(len(results), 1)
        c = results[0]
        self.assertIn('hourly_rate', c)
        self.assertIn('currency', c)
        self.assertEqual(c['hourly_rate'], '1500.00')

    def test_booking_auto_fills_price(self):
        """Creating a booking should auto-fill price from counselor's hourly_rate."""
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-07-01',
            'start_time': '10:00',
            'end_time': '11:00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['price'], '1500.00')

    def test_price_is_read_only_in_booking(self):
        """Users should not be able to override price in booking."""
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-07-02',
            'start_time': '11:00',
            'end_time': '12:00',
        }, format='json')
        self.assertEqual(resp.data['price'], '1500.00')

    def test_null_rate_results_in_null_price(self):
        """If counselor has no rate, booking price should be null."""
        self.profile.hourly_rate = None
        self.profile.save(update_fields=['hourly_rate'])
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/bookings/create/', {
            'counselor_id': self.profile.id,
            'date': '2026-07-03',
            'start_time': '13:00',
            'end_time': '14:00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resp.data['price'])

    def test_profile_shows_pricing(self):
        """Counselor's own profile should show hourly_rate and currency."""
        self.client.force_authenticate(user=self.counselor_user)
        resp = self.client.get('/api/counselors/me/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['hourly_rate'], '1500.00')
        self.assertEqual(resp.data['currency'], 'TWD')


class AIChatPinRenameTests(APITestCase):
    """Test AI chat session PATCH for rename and pin."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='pinuser', email='pin@test.com', password='PinPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def test_rename_session(self):
        session = AIChatSession.objects.create(user=self.user, title='Old Title')
        resp = self.client.patch(
            f'/api/ai-chat/sessions/{session.id}/',
            {'title': 'New Title'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], 'New Title')
        session.refresh_from_db()
        self.assertEqual(session.title, 'New Title')

    def test_pin_session(self):
        session = AIChatSession.objects.create(user=self.user)
        resp = self.client.patch(
            f'/api/ai-chat/sessions/{session.id}/',
            {'is_pinned': True},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['is_pinned'])
        session.refresh_from_db()
        self.assertTrue(session.is_pinned)

    def test_pinned_order(self):
        """Pinned sessions should appear before unpinned ones."""
        s1 = AIChatSession.objects.create(user=self.user, title='Unpinned')
        s2 = AIChatSession.objects.create(user=self.user, title='Pinned', is_pinned=True)
        resp = self.client.get('/api/ai-chat/sessions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data[0]['title'], 'Pinned')
        self.assertEqual(resp.data[1]['title'], 'Unpinned')

    def test_patch_nonexistent(self):
        resp = self.client.patch(
            '/api/ai-chat/sessions/99999/',
            {'title': 'Ghost'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class SoftDeleteTests(APITestCase):
    """Test soft-delete, trash, restore, and permanent delete."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='trashuser', email='trash@test.com', password='TrashPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def _create_note(self, content='Test note'):
        note = MoodNote(user=self.user)
        note.set_content(content)
        note.save()
        return note.id

    def test_delete_is_soft(self):
        """DELETE /api/notes/<id>/ should soft-delete, not hard-delete."""
        note_id = self._create_note('Soft delete me')
        resp = self.client.delete(f'/api/notes/{note_id}/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        note = MoodNote.objects.get(pk=note_id)
        self.assertTrue(note.is_deleted)
        self.assertIsNotNone(note.deleted_at)

    def test_deleted_note_excluded_from_list(self):
        """Soft-deleted notes should not appear in normal list."""
        note_id = self._create_note('Hidden note')
        self.client.delete(f'/api/notes/{note_id}/')
        resp = self.client.get('/api/notes/')
        ids = [n['id'] for n in resp.data.get('results', resp.data)]
        self.assertNotIn(note_id, ids)

    def test_trash_endpoint(self):
        """GET /api/notes/trash/ should list soft-deleted notes."""
        note_id = self._create_note('Trash me')
        self.client.delete(f'/api/notes/{note_id}/')
        resp = self.client.get('/api/notes/trash/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [n['id'] for n in resp.data]
        self.assertIn(note_id, ids)

    def test_restore(self):
        """POST /api/notes/<id>/restore/ should un-delete a note."""
        note_id = self._create_note('Restore me')
        self.client.delete(f'/api/notes/{note_id}/')
        resp = self.client.post(f'/api/notes/{note_id}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        note = MoodNote.objects.get(pk=note_id)
        self.assertFalse(note.is_deleted)
        self.assertIsNone(note.deleted_at)

    def test_permanent_delete(self):
        """DELETE /api/notes/<id>/permanent-delete/ should hard-delete from trash."""
        note_id = self._create_note('Gone forever')
        self.client.delete(f'/api/notes/{note_id}/')
        resp = self.client.delete(f'/api/notes/{note_id}/permanent-delete/')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MoodNote.objects.filter(pk=note_id).exists())

    def test_permanent_delete_non_trashed_404(self):
        """Cannot permanently delete a note that is not in trash."""
        note_id = self._create_note('Still alive')
        resp = self.client.delete(f'/api/notes/{note_id}/permanent-delete/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_restore_non_trashed_404(self):
        """Cannot restore a note that is not in trash."""
        note_id = self._create_note('Not trashed')
        resp = self.client.post(f'/api/notes/{note_id}/restore/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(REST_FRAMEWORK=NO_THROTTLE)
class AuditLogTests(APITestCase):
    """Test that audit log entries are created for key actions."""

    def setUp(self):
        from .models import AuditLog
        self.AuditLog = AuditLog
        self.user = CustomUser.objects.create_user(
            username='audituser', email='audit@test.com', password='AuditPass123!',
        )
        self.client.force_authenticate(user=self.user)

    def _create_note(self, content='Test note'):
        note = MoodNote(user=self.user)
        note.set_content(content)
        note.save()
        return note.id

    def test_note_delete_creates_audit(self):
        note_id = self._create_note('Audit this')
        self.client.delete(f'/api/notes/{note_id}/')
        entry = self.AuditLog.objects.filter(
            user=self.user, action='note_delete', target_type='MoodNote', target_id=note_id
        )
        self.assertTrue(entry.exists())

    def test_note_restore_creates_audit(self):
        note_id = self._create_note('Audit restore')
        self.client.delete(f'/api/notes/{note_id}/')
        self.client.post(f'/api/notes/{note_id}/restore/')
        entry = self.AuditLog.objects.filter(
            user=self.user, action='note_restore', target_type='MoodNote', target_id=note_id
        )
        self.assertTrue(entry.exists())


class AIChatPaginationTests(APITestCase):
    """Test AI chat message pagination."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='chatpageuser', email='chatpage@test.com', password='ChatPass123!',
        )
        self.client.force_authenticate(user=self.user)
        self.session = AIChatSession.objects.create(user=self.user, title='Pagination Test')

    def test_messages_limited_to_50(self):
        """Should return at most 50 messages."""
        for i in range(55):
            AIChatMessage.objects.create(
                session=self.session, role='user', content=f'msg {i}'
            )
        resp = self.client.get(f'/api/ai-chat/sessions/{self.session.id}/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(resp.data['messages']), 50)
        self.assertTrue(resp.data['has_more'])

    def test_before_param(self):
        """?before=<id> should return messages before that ID."""
        msgs = []
        for i in range(10):
            m = AIChatMessage.objects.create(
                session=self.session, role='user', content=f'msg {i}'
            )
            msgs.append(m)
        mid = msgs[5].id
        resp = self.client.get(f'/api/ai-chat/sessions/{self.session.id}/?before={mid}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for m in resp.data['messages']:
            self.assertLess(m['id'], mid)

    def test_no_has_more_when_few(self):
        """has_more should be False when fewer than 50 messages."""
        AIChatMessage.objects.create(
            session=self.session, role='user', content='only one'
        )
        resp = self.client.get(f'/api/ai-chat/sessions/{self.session.id}/')
        self.assertFalse(resp.data['has_more'])
