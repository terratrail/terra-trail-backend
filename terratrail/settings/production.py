"""
TerraTrail — Production settings.
Optimised for Render.com deployment.
"""

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
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Database — PostgreSQL via DATABASE_URL
# ---------------------------------------------------------------------------

import os
from decouple import config

# Decouple will look at environment variables first, then your .env file
db_url = config("DATABASE_URL", default=config("INTERNAL_DATABASE_URL", default=None))

DATABASES = {
    "default": dj_database_url.config(
        default=db_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

if not DATABASES.get("default"):
    import sys
    sys.stderr.write("\n" + "="*50 + "\n")
    sys.stderr.write("CRITICAL: DATABASE_URL not found!\n")
    sys.stderr.write(f"Available Env Keys: {', '.join(os.environ.keys())}\n")
    sys.stderr.write("Note: If running locally, check your .env file.\n")
    sys.stderr.write("="*50 + "\n")

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
