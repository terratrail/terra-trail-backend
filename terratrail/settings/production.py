"""
TerraTrail — Production settings.
Optimised for Railway deployment.

Can be loaded directly (DJANGO_SETTINGS_MODULE=terratrail.settings.production)
or via the package __init__.py (DJANGO_SETTINGS_MODULE=terratrail.settings).
"""

from .base import *  # noqa: F401,F403 — must come first; provides ROOT_URLCONF, INSTALLED_APPS, etc.
from decouple import config
import dj_database_url

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
# Railway (and most cloud platforms) terminate SSL at the proxy — the service
# receives plain HTTP internally. Setting this True would redirect internal
# healthchecks to HTTPS, which the Railway healthchecker can't reach.
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # Trust Railway's proxy
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Database — PostgreSQL via DATABASE_URL
# ---------------------------------------------------------------------------

import os

# Railway injects DATABASE_URL automatically when a Postgres service is linked.
# os.environ is checked before any .env file, so Railway's value always wins.
_db_url = os.environ.get("DATABASE_URL") or config("DATABASE_URL", default=None)

if not _db_url:
    import sys

    sys.stderr.write("\n" + "=" * 50 + "\n")
    sys.stderr.write("CRITICAL: DATABASE_URL is not set!\n")
    sys.stderr.write(
        "On Railway: link a Postgres service or set DATABASE_URL in Variables.\n"
    )
    sys.stderr.write(f"Available env keys: {', '.join(sorted(os.environ.keys()))}\n")
    sys.stderr.write("=" * 50 + "\n")

DATABASES = {
    "default": dj_database_url.parse(
        _db_url or "sqlite:///db.sqlite3",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# ---------------------------------------------------------------------------
# Email — Resend (overrides base.py's decouple-based default)
# ---------------------------------------------------------------------------

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="notifications.resend_backend.ResendEmailBackend",
)
RESEND_API_KEY = config("RESEND_API_KEY", default="")
MAIL_DOMAIN = config("MAIL_DOMAIN", default="mail.terratrail.app")

# ---------------------------------------------------------------------------
# Storage — S3
# ---------------------------------------------------------------------------

AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Logging — stdout only (Render captures stdout; file paths don't persist)
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} [{name}:{lineno}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "terratrail": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "accounts": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "properties": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "customers": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "payments": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "commissions": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "notifications": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
