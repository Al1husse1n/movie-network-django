from .dev import *

# Ensure staticfiles directory exists in tests to silence WhiteNoise stat warning
(BASE_DIR / "staticfiles").mkdir(exist_ok=True)

# Use MD5 password hasher in tests — 10-50x faster than PBKDF2.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Silence logging noise.
LOGGING_CONFIG = None

# Celery: run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Channels: use in-memory channel layer for tests
CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}

# Cache: use fast in-memory cache in tests instead of Redis
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Storages: use standard staticfiles storage in tests to avoid whitenoise manifest stat overhead
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
