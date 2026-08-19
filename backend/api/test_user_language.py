"""Contract tests for the per-account UI language preference.

The frontend used to keep the language in localStorage only, which is
per-browser rather than per-account: signing into an English demo account on a
machine that had ever used the app left the UI in Traditional Chinese, and
because ``Accept-Language`` is sent from that same value, the AI-generated
daily writing prompt came back in Chinese as well.

``CustomUser.language`` is what the frontend now adopts on login, so these
tests pin the parts the client depends on: the field is readable, writable,
validated, and defaults to zh-TW for everyone who never set it.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


class UserLanguagePreferenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='langtest', password='pw-for-test-1')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_defaults_to_zh_tw(self):
        """Existing accounts must not silently flip language when the column
        is added — the migration backfills zh-TW and so does the model."""
        self.assertEqual(self.user.language, 'zh-TW')

    def test_profile_exposes_language(self):
        resp = self.client.get('/api/auth/profile/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['language'], 'zh-TW')

    def test_profile_accepts_language_patch(self):
        resp = self.client.patch('/api/auth/profile/', {'language': 'en'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'en')

    def test_profile_rejects_unknown_language(self):
        """The client sends this value straight from a menu, but a rejected
        value must not land in the column — the frontend falls back to English
        then zh-TW for unknown codes, so a bad value would show as a silently
        mistranslated UI rather than an error."""
        resp = self.client.patch('/api/auth/profile/', {'language': 'klingon'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, 'zh-TW')

    def test_all_supported_locales_round_trip(self):
        for code in ('zh-TW', 'en', 'ja'):
            with self.subTest(code=code):
                resp = self.client.patch(
                    '/api/auth/profile/', {'language': code}, format='json',
                )
                self.assertEqual(resp.status_code, 200)
                self.assertEqual(resp.data['language'], code)


class DemoAccountLanguageTests(TestCase):
    """The English demo accounts exist so an overseas reviewer sees a whole
    English app; they are useless if the seed forgets to stamp the language."""

    def test_seed_stamps_language_on_english_accounts(self):
        from api.management.commands.seed_demo_test_accounts_en import (
            ACCOUNT_LANGUAGE, ACCOUNT_TIMEZONE,
        )
        self.assertEqual(ACCOUNT_LANGUAGE, 'en')
        # Timezone and language have to agree, or weekday charts and the UI
        # tell the reviewer two different stories.
        self.assertTrue(ACCOUNT_TIMEZONE.startswith('America/'))
