"""
TerraTrail — Production settings.
"""

from decouple import config

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)

# ---------------------------------------------------------------------------
# Database — PostgreSQL in production
# ---------------------------------------------------------------------------

import dj_database_url

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="terratrail"),
        "USER": config("DB_USER", default="terratrail"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# DATABASES = {
#     "default": dj_database_url.config(
#         default=config("DATABASE_URL", default="postgres://localhost/terratrail"),
#         conn_max_age=600,
#         conn_health_checks=True,
#     )
# }

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
