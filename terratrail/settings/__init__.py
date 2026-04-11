from .base import *  # noqa: F401,F403
from decouple import config

DEBUG = config("DEBUG", default=True, cast=bool)

if DEBUG:
    from .development import *  # noqa: F401,F403

    # Dev-only app additions (safe because base.py's INSTALLED_APPS is in scope)
    try:
        import django_extensions  # noqa: F401
        INSTALLED_APPS += ["django_extensions"]  # noqa: F405
    except ImportError:
        pass
else:
    from .production import *  # noqa: F401,F403
