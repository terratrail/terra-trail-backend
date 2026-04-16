"""
TerraTrail — Base Django settings.

Shared configuration for all environments.
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-dev-only-change-in-production",
)

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1,.localhost", cast=Csv()
)

# settings.py
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-workspace-slug",  # Add this line
]


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_beat",
    "drf_yasg",
]

LOCAL_APPS = [
    "core",
    "accounts",
    "properties",
    "customers",
    "payments",
    "commissions",
    "notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.WorkspaceMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "terratrail.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "terratrail.wsgi.application"
ASGI_APPLICATION = "terratrail.asgi.application"


# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"


# ---------------------------------------------------------------------------
# Database (overridden per environment)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static & Media files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "core.renderers.StandardResponseRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%SZ",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "120/minute",
        "otp_request": "5/minute",
        "otp_verify": "10/minute",
    },
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60, cast=int)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7, cast=int)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": config("JWT_ALGORITHM", default="HS256"),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
}

SWAGGER_SETTINGS = {
    "DEFAULT_AUTO_SCHEMA_CLASS": "drf_yasg.inspectors.SwaggerAutoSchema",
    "USE_SESSION_AUTH": True,  # Disable session auth if not needed
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:3000,http://127.0.0.1:3000",
    cast=Csv(),
)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@terratrail.io")


# ---------------------------------------------------------------------------
# OTP Configuration
# ---------------------------------------------------------------------------

OTP_EXPIRY_MINUTES = config("OTP_EXPIRY_MINUTES", default=10, cast=int)
OTP_MAX_ATTEMPTS = config("OTP_MAX_ATTEMPTS", default=3, cast=int)
OTP_LOCKOUT_MINUTES = config("OTP_LOCKOUT_MINUTES", default=15, cast=int)
CUSTOMER_SESSION_TIMEOUT_MINUTES = config(
    "CUSTOMER_SESSION_TIMEOUT_MINUTES", default=30, cast=int
)


# ---------------------------------------------------------------------------
# SMS Configuration (abstracted)
# ---------------------------------------------------------------------------

SMS_PROVIDER = config("SMS_PROVIDER", default="console")
SMS_API_KEY = config("SMS_API_KEY", default="")
SMS_SENDER_ID = config("SMS_SENDER_ID", default="TerraTrail")


# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Used for file logs — includes module path and line number
        "verbose": {
            "format": "{levelname} {asctime} [{name}:{lineno}] {message}",
            "style": "{",
        },
        # Used for console — clean module-path format
        "simple": {
            "format": "{levelname} {asctime} [{name}] {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/terratrail.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs/errors.log",
            "maxBytes": 1024 * 1024 * 5,  # 5 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        # Django internals — only warnings and above; avoids flooding the
        # console with migration hints, template debug info, etc.
        "django": {
            "handlers": ["console", "file", "error_file"],
            "level": "WARNING",
            "propagate": False,
        },
        # Dev-server HTTP access log (basehttp.py) — silenced at WARNING
        # so 200/304 static-file requests don't fill the console.
        "django.server": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        # 5xx errors from request handling → email admins + error file
        "django.request": {
            "handlers": ["mail_admins", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        # ── Project loggers ────────────────────────────────────────────────
        # Each app declares: logger = logging.getLogger(__name__)
        # which resolves to e.g. "accounts.services", "properties.views".
        # All project loggers propagate up to "terratrail" by default,
        # so individual app entries are only needed for overrides.
        "terratrail": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "accounts": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "properties": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "customers": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "payments": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "commissions": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "notifications": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
