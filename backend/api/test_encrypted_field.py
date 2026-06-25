"""Unit tests for EncryptedTextField transparent encryption.

The field is in production use on three columns:
  * MoodNote.ai_feedback
  * AIChatMessage.content
  * WeeklySummary.ai_summary

These tests verify the read/write transparency, empty-string preservation,
idempotency (double-write doesn't double-encrypt), and the DB-level
ciphertext shape (so a DBA dumping the table sees Fernet tokens, not
plaintext).
"""
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase

from api.models import AIChatMessage, AIChatSession, MoodNote, WeeklySummary
from datetime import date


User = get_user_model()


class EncryptedTextFieldTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='enc-test', email='enc@test.local', password='pw'
        )

    def _raw_cell(self, table, column, pk):
        with connection.cursor() as cur:
            cur.execute(
                f'SELECT {column} FROM {table} WHERE id = %s', [pk]
            )
            return cur.fetchone()[0]

    # ------------------------------------------------------------------
    # MoodNote.ai_feedback
    # ------------------------------------------------------------------
    def test_moodnote_ai_feedback_round_trip(self):
        note = MoodNote(user=self.user, encrypted_content='ignored')
        note.set_content('today felt heavy')
        note.ai_feedback = '我聽到你了。今天請好好休息。'
        note.save()

        # Refetch — round-trip through DB + from_db_value.
        loaded = MoodNote.objects.get(pk=note.pk)
        self.assertEqual(loaded.ai_feedback, '我聽到你了。今天請好好休息。')

    def test_moodnote_ai_feedback_db_is_ciphertext(self):
        note = MoodNote(user=self.user, encrypted_content='x')
        note.set_content('text')
        note.ai_feedback = 'secret advice that DBA must not see'
        note.save()

        raw = self._raw_cell('api_moodnote', 'ai_feedback', note.pk)
        # Fernet ciphertext: long, base64-safe, starts with 'gAAAAA'.
        self.assertTrue(raw.startswith('gAAAAA'), f'expected ciphertext, got: {raw[:40]!r}')
        self.assertNotIn('secret advice', raw,
                         'plaintext leaked into DB column')

    def test_moodnote_ai_feedback_empty_preserved(self):
        note = MoodNote(user=self.user, encrypted_content='x')
        note.set_content('text')
        note.ai_feedback = ''
        note.save()

        raw = self._raw_cell('api_moodnote', 'ai_feedback', note.pk)
        self.assertEqual(raw, '', 'empty must stay empty (not encrypted into a token)')
        # __gt='' filter must keep working on encrypted column.
        self.assertFalse(MoodNote.objects.filter(pk=note.pk, ai_feedback__gt='').exists())

    def test_moodnote_ai_feedback_existence_filter_works(self):
        n1 = MoodNote(user=self.user, encrypted_content='x')
        n1.set_content('a'); n1.ai_feedback = ''; n1.save()
        n2 = MoodNote(user=self.user, encrypted_content='x')
        n2.set_content('b'); n2.ai_feedback = '有回饋'; n2.save()
        # achievements.py + 0056/0058 migrations depend on __gt='' identifying
        # rows-with-real-content.
        ids = set(MoodNote.objects.filter(ai_feedback__gt='').values_list('pk', flat=True))
        self.assertIn(n2.pk, ids)
        self.assertNotIn(n1.pk, ids)

    def test_moodnote_idempotent_save_does_not_double_encrypt(self):
        note = MoodNote(user=self.user, encrypted_content='x')
        note.set_content('text')
        note.ai_feedback = 'hello'
        note.save()
        first_raw = self._raw_cell('api_moodnote', 'ai_feedback', note.pk)

        # Save again without changing the field — the value Django sees in
        # memory is already plaintext (from from_db_value on the previous
        # access), so re-saving must NOT wrap a fresh Fernet token around it.
        loaded = MoodNote.objects.get(pk=note.pk)
        self.assertEqual(loaded.ai_feedback, 'hello')
        loaded.save()
        second_raw = self._raw_cell('api_moodnote', 'ai_feedback', note.pk)
        # Either identical (no rewrite) or a fresh ciphertext that still
        # decrypts to the same plaintext.
        again = MoodNote.objects.get(pk=note.pk)
        self.assertEqual(again.ai_feedback, 'hello')

    # ------------------------------------------------------------------
    # AIChatMessage.content
    # ------------------------------------------------------------------
    def test_aichatmessage_content_round_trip(self):
        session = AIChatSession.objects.create(user=self.user)
        msg = AIChatMessage.objects.create(
            session=session, role='user', content='我最近壓力好大',
        )
        loaded = AIChatMessage.objects.get(pk=msg.pk)
        self.assertEqual(loaded.content, '我最近壓力好大')

        raw = self._raw_cell('api_aichatmessage', 'content', msg.pk)
        self.assertTrue(raw.startswith('gAAAAA'))
        self.assertNotIn('壓力好大', raw)

    def test_aichatmessage_str_uses_decrypted(self):
        session = AIChatSession.objects.create(user=self.user)
        msg = AIChatMessage.objects.create(
            session=session, role='assistant', content='我聽到你說的了',
        )
        self.assertIn('我聽到你說的了', str(msg))

    # ------------------------------------------------------------------
    # WeeklySummary.ai_summary
    # ------------------------------------------------------------------
    def test_weeklysummary_ai_summary_round_trip(self):
        ws = WeeklySummary.objects.create(
            user=self.user,
            week_start=date(2026, 6, 22),
            note_count=5,
            ai_summary='本週情緒呈現下行趨勢，建議...',
        )
        loaded = WeeklySummary.objects.get(pk=ws.pk)
        self.assertEqual(loaded.ai_summary, '本週情緒呈現下行趨勢，建議...')
        raw = self._raw_cell('api_weeklysummary', 'ai_summary', ws.pk)
        self.assertTrue(raw.startswith('gAAAAA'))
