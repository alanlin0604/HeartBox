import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """AES-256 Fernet encryption service (singleton)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            key = settings.ENCRYPTION_KEY
            if not key:
                key = Fernet.generate_key().decode()
                logger.warning(
                    'ENCRYPTION_KEY not set — generated a temporary key. '
                    'Set ENCRYPTION_KEY in .env for persistent encryption.'
                )
            cls._instance._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return cls._instance

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode('utf-8')).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            logger.error('Failed to decrypt content — invalid token or wrong key')
            return '[解密失敗]'


encryption_service = EncryptionService()
