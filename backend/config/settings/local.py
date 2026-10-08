"""Local development settings."""

import socket

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend"]

# --- CORS (allow frontend dev server) ---
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# --- CSRF ---
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# --- Session cookies (relaxed for local dev) ---
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# --- Email (Mailpit) ---
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# If postgres host is unresolvable (e.g. running pytest directly outside docker), fallback to sqlite
db_host = DATABASES["default"]["HOST"]
if db_host == "postgres":
    try:
        socket.gethostbyname("postgres")
    except socket.gaierror:
        DATABASES["default"] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
