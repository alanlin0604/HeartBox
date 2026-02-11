import logging
import threading

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """AES-256 Fernet encryption service (singleton)."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    key = settings.ENCRYPTION_KEY
                    if not key:
                        raise RuntimeError(
                            'ENCRYPTION_KEY is not set. '
                            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" '
                            'and add it to your .env file.'
                        )
                    try:
                        cls._instance._fernet = Fernet(key.encode() if isinstance(key, str) else key)
                    except Exception as e:
                        cls._instance = None
                        raise RuntimeError(f'Invalid ENCRYPTION_KEY: {e}')
        return cls._instance

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            logger.error('Failed to decrypt content — invalid token or wrong key')
            return '[Decryption failed]'


encryption_service = EncryptionService()
