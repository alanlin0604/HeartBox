"""Test settings — force SQLite regardless of DATABASE_URL."""
from .settings import *  # noqa: F401, F403
from pathlib import Path

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': Path(__file__).resolve().parent.parent / 'test_db.sqlite3',
    }
}

# Disable production security settings for testing
SECURE_SSL_REDIRECT = False
