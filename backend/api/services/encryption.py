import logging
import threading

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

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


encryption_service = EncryptionService()
