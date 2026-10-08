"""Production settings."""

import os

from .base import *  # noqa: F401, F403

DEBUG = False

if not os.environ.get("DJANGO_SECRET_KEY"):
    raise ValueError("DJANGO_SECRET_KEY environment variable is required in production")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
if not any(ALLOWED_HOSTS):
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set in production")

# --- Security ---
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Secure Cookies ---
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# --- CORS (must be explicitly set) ---
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")
if not any(CORS_ALLOWED_ORIGINS):
    raise ValueError("CORS_ALLOWED_ORIGINS must be set in production")

# --- CSRF ---
CSRF_TRUSTED_ORIGINS = os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")

# --- Email (production SMTP) ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_USE_TLS = True
