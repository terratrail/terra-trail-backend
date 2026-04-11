from .base import *  # noqa: F401,F403
from decouple import config

DEBUG = config("DEBUG", default=True, cast=bool)

if DEBUG:
    from .development import *  # noqa: F401,F403
else:
    from .production import *  # noqa: F401,F403
