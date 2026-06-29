import os
from pathlib import Path
from datetime import timedelta

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root (one level above backend/)
load_dotenv(BASE_DIR.parent / '.env')

_secret = os.getenv('DJANGO_SECRET_KEY', '')
if not _secret:
    raise RuntimeError('DJANGO_SECRET_KEY is not set. Add it to your .env file.')
SECRET_KEY = _secret
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'drf_spectacular',
    'django_celery_beat',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Local
    'api',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'api.middleware.UserTimezoneMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.ContentSecurityPolicyMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'moodnotes_pro.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'moodnotes_pro.wsgi.application'
ASGI_APPLICATION = 'moodnotes_pro.asgi.application'

# Channels — InMemoryChannelLayer everywhere.
#
# History: tried channels_redis pointing at Upstash (rediss://) on
# 2026-05-23 but Cloud Run instances can't DNS-resolve
# `pleasant-anteater-37478.upstash.io` ("Error -2 ... Name or service
# not known"), so every group_send raised and `note_analyzed` events
# never reached the consumer. Reverted 2026-05-24.
#
# Trade-off: InMemoryChannelLayer is per-process, so cross-instance
# WS fan-out doesn't work. We mitigate by pinning Cloud Run to a single
# instance (`--min-instances=1 --max-instances=1`). At current load
# (<100 daily users) that's plenty; scaling out is deferred until we
# stand up Memorystore or fix the Upstash DNS path.
#
# If you ever raise max-instances above 1, you MUST restore a real
# cross-process broker — otherwise a user whose note POST lands on
# instance A while their WS is on instance B will silently miss
# `note_analyzed` and have to refresh.
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}
# Cache uses REDIS_URL only when set EXPLICITLY (not the CELERY fallback).
# Local memory cache works in production too — Cloud Run keeps min-instances
# warm so the locmem hit rate is fine, and skipping a Redis connect on
# every cold start avoids a DNS race I hit when REDIS_URL was first set.
REDIS_URL = os.getenv('REDIS_URL')

# Database — Neon PostgreSQL via DATABASE_URL, fallback to SQLite
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True),
    }
    DATABASES['default']['CONN_HEALTH_CHECKS'] = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'api.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Argon2 first so new passwords use the modern memory-hard hash; PBKDF2 stays
# in the list so existing PBKDF2 hashes still verify (Django will transparently
# upgrade them to Argon2 on the next successful login).
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

LANGUAGE_CODE = 'zh-hant'
LANGUAGES = [
    ('zh-hant', 'Traditional Chinese'),
    ('en', 'English'),
    ('ja', 'Japanese'),
]
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Google Cloud Storage for media (production)
GS_BUCKET_NAME = os.getenv('GS_BUCKET_NAME', '')
if GS_BUCKET_NAME:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.gcloud.GoogleCloudStorage',
    }
    GS_DEFAULT_ACL = None
    GS_QUERYSTRING_AUTH = False
    MEDIA_URL = f'https://storage.googleapis.com/{GS_BUCKET_NAME}/'

# CORS
if DEBUG:
    CORS_ALLOWED_ORIGINS = [f'http://localhost:{p}' for p in range(5173, 5180)]
    CSRF_TRUSTED_ORIGINS = [f'http://localhost:{p}' for p in range(5173, 5180)]
    CORS_ALLOW_CREDENTIALS = True
else:
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(',')
    CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173').split(',')

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'api.authentication.VersionedJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Disable DRF intercepting ?format= query param (we use it for PDF export)
    'URL_FORMAT_OVERRIDE': None,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # The journal home page alone fires ~8 GET requests on first
        # navigation (notes, sleep, daily-prompt, tags, analytics, alerts,
        # notifications, personal-suggestion). Add WebSocket reconnects,
        # tab switches, and an active session can blow past 200/hour in
        # ~25 navigations. Raised default to 2000/hour (~33/min average,
        # plenty of burst headroom for normal use). Set THROTTLE_USER in
        # Cloud Run env to override per environment.
        'user': os.getenv('THROTTLE_USER', '2000/hour'),
        'login': os.getenv('THROTTLE_LOGIN', '30/hour'),
        'login_per_username': os.getenv('THROTTLE_LOGIN_PER_USERNAME', '10/hour'),
        'register': os.getenv('THROTTLE_REGISTER', '5/hour'),
        'password_reset': os.getenv('THROTTLE_PASSWORD_RESET', '5/hour'),
        'note_create': '30/hour',
        'upload': '50/hour',
        'export': '5/hour',
        'booking': '20/hour',
        'message_send': '60/hour',
        'ai_chat': '30/hour',
        'delete_account': '5/hour',
        'token_refresh': '30/hour',
        'general_write': '30/minute',
        'anon': '100/hour',
    },
}

# JWT
# 15-min access keeps the bearer-token blast radius tight; refresh rotation
# + blacklist makes the long-lived refresh single-use. token_version is
# bumped on logout/password change/2FA disable so any access token issued
# before that moment is rejected immediately on its next use.
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Encryption
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', '')
if ENCRYPTION_KEY:
    import base64
    try:
        decoded = base64.urlsafe_b64decode(ENCRYPTION_KEY)
        if len(decoded) != 32:
            raise ValueError('Key must be 32 url-safe base64-encoded bytes')
    except Exception as e:
        raise RuntimeError(f'Invalid ENCRYPTION_KEY: {e}. Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')

# LLM provider — talks to the self-hosted FastAPI inference server
# (TAIDE for chat / LLaVA for vision), reached via Cloudflare Tunnel.
# No external AI vendor is contacted in production; user journal data
# never leaves Taiwan-resident infrastructure.
#
# LLM_PROVIDER:
#   - 'remote_taide' (default) — talk to llm_server over HTTP, OpenAI-compat shape
#   - 'mock'                   — deterministic stub for tests
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'remote_taide')
# Empty default — caller's `is_configured()` returns False until both URL and
# API key are set, so daily-prompt / weekly-summary endpoints silently skip
# AI rather than blocking 10s on a connect timeout to a dead localhost.
LLM_SERVER_URL = os.getenv('LLM_SERVER_URL', '')
LLM_SERVER_API_KEY = os.getenv('LLM_SERVER_API_KEY', '')
LLM_MODEL = os.getenv('LLM_MODEL', 'taide-lx-7b-chat')
LLM_VISION_MODEL = os.getenv('LLM_VISION_MODEL', 'llava-v1.6-mistral-7b')
# `or '30'` handles the present-but-empty case (`LLM_TIMEOUT_S=` in env);
# bare os.getenv default only fires when the var is absent, so we'd crash
# at import time on Cloud Run if an operator cleared the row without
# removing it.
LLM_TIMEOUT_S = float(os.getenv('LLM_TIMEOUT_S') or '30')

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv('CHROMA_PERSIST_DIR', str(BASE_DIR / 'chroma_db'))
# BGE-M3 vectors are 1024-dim; OpenAI's were 1536-dim. The collection
# name must change because Chroma rejects mismatched-dim inserts.
CHROMA_COLLECTION_NAME = os.getenv('CHROMA_COLLECTION_NAME', 'psychology_kb_bgem3')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

# Email
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@heartbox.local')
PASSWORD_RESET_TIMEOUT = 900  # 15 minutes

# WebSocket auth — first-message JWT is the only supported path.
# QS tokens leak into access logs / history; keep disabled in prod.
WS_ALLOW_QUERY_STRING_TOKEN = os.getenv('WS_ALLOW_QUERY_STRING_TOKEN', 'False').lower() in ('true', '1', 'yes')

# Celery
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL or 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Taipei'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# DRF Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'HeartBox API',
    'DESCRIPTION': 'AI-powered encrypted mood journal application',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Google OAuth
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
        },
        'SCOPE': ['email', 'profile'],
        'AUTH_PARAMS': {'access_type': 'online'},
    },
}

# WhiteNoise immutable file caching (files have content hashes)
WHITENOISE_MAX_AGE = 31536000

# Cache
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        },
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }

# Logging
# RedactEmailFilter scrubs email addresses out of log records before they
# leave the process. Cloud Logging / Sentry indexes log bodies; an email
# in there becomes a PII pivot point. The replacement is u<sha256[:8]>@<domain>
# so two log lines about the same user can still be correlated for
# operational debugging without exposing the actual address.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'redact_email': {
            '()': 'api.services.log_filters.RedactEmailFilter',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['redact_email'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'api': {
            'handlers': ['console'],
            'level': 'WARNING' if not DEBUG else 'DEBUG',
        },
    },
}

# Production security
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
    # CORP defaults to same-origin so attached resources (avatars, exports)
    # can't be embedded cross-origin; pairs with COOP above.
    SECURE_CROSS_ORIGIN_RESOURCE_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    # Lock the cookie to first-party context only
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    # CSRF cookie is read by the JS frontend on regular Django form submission
    # but not on our DRF JWT API. Make it HttpOnly so a successful XSS payload
    # can't steal it for a CSRF chain.
    CSRF_COOKIE_HTTPONLY = True

# Upload limits — Django defaults are 2.5 MB; tighten the JSON / form body
# accepted by APIs and rely on per-endpoint magic-byte validation for files.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB total request body
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024   # 5 MB per file (avatar/attachment further capped per-serializer)
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000            # default 1000, keep explicit

# Content Security Policy (via SecurityMiddleware headers)
# `wss:` + `https:` wildcards in connect-src are still here because the
# frontend is cross-origin (Cloudflare Pages → Cloud Run) and the websocket
# host is env-driven. Narrow this to explicit hosts once CSP_ALLOWED_API_HOST
# is set in env.
_csp_api_host = os.getenv('CSP_API_HOST', '').strip()
_csp_ws_host = os.getenv('CSP_WS_HOST', '').strip()
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Tailwind utility classes / inline runtime
CSP_IMG_SRC = ("'self'", "data:", "blob:", "https://storage.googleapis.com")
CSP_CONNECT_SRC = (
    "'self'",
    _csp_api_host or "https:",
    _csp_ws_host or "wss:",
)
CSP_FONT_SRC = ("'self'", "data:")
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)

# Sentry error tracking (set SENTRY_DSN in .env to activate)
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    import sentry_sdk

    _SENSITIVE_PATH_PARTS = ('/notes/', '/ai-chat/', '/messages/', '/community/posts')
    _SENSITIVE_HEADERS = {'authorization', 'cookie', 'x-cron-secret'}

    def _sentry_scrub(event, hint):
        """Strip plaintext journal/chat content + auth headers before send.

        send_default_pii=False already drops user PII, but request bodies on
        mood-note / AI chat / community POSTs can carry the journal text
        BEFORE it's encrypted. Hide them at the source.
        """
        try:
            req = event.get('request') or {}
            url = req.get('url') or ''
            if any(part in url for part in _SENSITIVE_PATH_PARTS):
                if 'data' in req:
                    req['data'] = '<redacted: sensitive endpoint>'
            # Always scrub auth-bearing headers
            headers = req.get('headers') or {}
            for k in list(headers.keys()):
                if k.lower() in _SENSITIVE_HEADERS:
                    headers[k] = '<redacted>'
        except Exception:
            pass
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        before_send=_sentry_scrub,
    )
    # Tag the LLM provider + model so error events are filterable in Sentry
    # by which inference backend was in use. Helpful when triaging "AI
    # broken" reports — quickly know if the user was on remote_taide or
    # the mock provider when the error fired.
    sentry_sdk.set_tag('llm_provider', LLM_PROVIDER)
    sentry_sdk.set_tag('llm_model', LLM_MODEL)
