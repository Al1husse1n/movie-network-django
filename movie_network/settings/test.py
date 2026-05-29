from .dev import *

# Use MD5 password hasher in tests — 10-50x faster than PBKDF2.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# Silence logging noise.
LOGGING_CONFIG = None
