"""
TerraTrail — Development settings.
"""

# DEBUG is already True when this file loads.
# Use SQLite for easy local setup.

CORS_ALLOW_ALL_ORIGINS = True

# Add browsable API in development
REST_FRAMEWORK_EXTRA = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# Extend installed apps for dev tooling
try:
    import django_extensions  # noqa: F401
    INSTALLED_APPS += ["django_extensions"]  # noqa: F821
except ImportError:
    pass
