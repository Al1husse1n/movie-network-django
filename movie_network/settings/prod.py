"""
Production settings for movie_network project.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *

# Fail-fast security checks for production environment
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY is required in production.")
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL is required in production.")
if not TMDB_API_KEY:
    raise ImproperlyConfigured("TMDB_API_KEY is required in production.")

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS is required in production.")

# Security Hardening
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
