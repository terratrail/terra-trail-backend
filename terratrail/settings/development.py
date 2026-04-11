"""
TerraTrail — Development settings.
"""

# DEBUG is already True when this file loads (set in base.py).
# Use SQLite for easy local setup.

CORS_ALLOW_ALL_ORIGINS = True

# The browsable API renderer is useful during development.
# Extend REST_FRAMEWORK in base.py by overriding DEFAULT_RENDERER_CLASSES
# at the view level if needed, rather than mutating the dict here.
