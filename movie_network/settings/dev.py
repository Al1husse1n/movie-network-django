"""
Development settings for movie_network project.
"""

from .base import *

DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"])

# SQLite fallback exists ONLY in dev.py and ONLY when DATABASE_URL is absent.
# This ensures a fresh clone without .env still boots for local development.
# Target production database remains Neon (PostgreSQL).
if not DATABASES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
