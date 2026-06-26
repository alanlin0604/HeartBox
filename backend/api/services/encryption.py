import logging
import threading

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


class EncryptionService:
    """AES-256 Fernet encryption service (singleton).

    Supports key rotation: ENCRYPTION_KEY can be a comma-separated list of
    Fernet keys. The first key is used for encryption; all keys are tried
    for decryption. This allows rotating keys without losing access to
    old data.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    raw = settings.ENCRYPTION_KEY
                    if not raw:
                        raise RuntimeError(
                            'ENCRYPTION_KEY is not set. '
                            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" '
                            'and add it to your .env file.'
                        )
                    try:
                        keys = [k.strip() for k in raw.split(',') if k.strip()]
                        fernets = [Fernet(k.encode() if isinstance(k, str) else k) for k in keys]
                        cls._instance._multi = MultiFernet(fernets)
                        cls._instance._primary = fernets[0]
                    except Exception as e:
                        cls._instance = None
                        raise RuntimeError(f'Invalid ENCRYPTION_KEY: {e}')
        return cls._instance

    def encrypt(self, plaintext: str) -> str:
        return self._primary.encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._multi.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            logger.error('Failed to decrypt content — invalid token or wrong key')
            return '[Decryption failed]'

    def try_decrypt(self, ciphertext: str) -> str | None:
        """Strict decrypt that returns ``None`` on InvalidToken instead of
        swallowing the error into a sentinel string. Used by
        ``EncryptedTextField`` to discriminate "already ciphertext" from
        "plaintext, please encrypt" without confusing a legitimate
        ``'[Decryption failed]'`` plaintext payload with a failure result.
        """
        try:
            return self._multi.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            return None


encryption_service = EncryptionService()


class EncryptedTextField(models.TextField):
    """Transparent Fernet-encrypted TextField.

    Reads decrypt automatically (``from_db_value``); writes encrypt
    automatically (``get_prep_value``). At the schema layer this is still a
    ``text`` column so migrations don't change DB topology — only the cell
    contents become ciphertext.

    Why this is the right abstraction here:
      * `MoodNote.ai_feedback` / `WeeklySummary.ai_summary` /
        `AIChatMessage.content` are AI-derived paraphrases of user mental-
        health journals. They never participate in LIKE/regex/icontains
        filters in this codebase (audited 2026-06-25), only in
        empty/non-empty existence checks (e.g. `__gt=''`), which keep
        working on ciphertext because Fernet ciphertext is always non-empty.
      * Existing MoodNote.encrypted_content uses an explicit `set_content()`
        + property pair to encrypt content; that pattern requires every
        caller to switch to a setter. The transparent field is a drop-in
        replacement that requires zero call-site changes, which is exactly
        what we want for paraphrased AI output that flows through many
        consumers (ai_engine x3, ai_chat, health.py, scrub migrations, etc.).
      * Empty string is preserved as empty string — we don't encrypt ''
        into a multi-byte ciphertext, so `__gt=''` continues to identify
        rows with real content.

    Trade-off: serializer fields that expose the column will return decrypted
    plaintext to authorized API consumers. Authorization is the existing DRF
    permission layer (per-user scoping); the encryption layer only protects
    against DB-tier compromise (dump, BAK file, DBA snooping).
    """

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        plain = encryption_service.try_decrypt(value)
        if plain is None:
            # Pre-migration plaintext row, or somehow a non-Fernet value
            # snuck into the column. Don't 500 the API — surface the raw
            # bytes (no key material involved) and log with row context so
            # an operator can locate + repair / backfill it.
            model_name = getattr(self.model, '__name__', '?') if hasattr(self, 'model') else '?'
            field_name = getattr(self, 'name', '?')
            logger.warning(
                'EncryptedTextField decrypt_failed model=%s field=%s len=%d '
                '(pre-migration plaintext, or post-key-rotation orphan). '
                'Run reencrypt_notes management command to repair.',
                model_name, field_name, len(value) if value else 0,
                extra={'event': 'decrypt_failed', 'model': model_name, 'field': field_name},
            )
            return value
        return plain

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        if not isinstance(value, str):
            value = str(value)
        # Idempotency guard: if the in-memory value happens to already be
        # Fernet ciphertext (e.g. when Django re-saves a freshly loaded row
        # without touching the field), don't double-encrypt. ``try_decrypt``
        # returns None on InvalidToken so we discriminate "plaintext, must
        # encrypt" from "already ciphertext, pass through".
        if encryption_service.try_decrypt(value) is not None:
            return value
        return encryption_service.encrypt(value)
