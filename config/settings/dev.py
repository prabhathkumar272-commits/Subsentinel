"""
Development settings for SubSentinel.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
DEBUG = True

# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = ["*"]

# ---------------------------------------------------------------------------
# Database – SQLite for local development
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        "ATOMIC_REQUESTS": True,
    }
}

# ---------------------------------------------------------------------------
# Email – console backend for development
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Static files – disable hashed names in dev for easier debugging
# ---------------------------------------------------------------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Cache – local memory for development
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ---------------------------------------------------------------------------
# django-axes – relax in development
# ---------------------------------------------------------------------------
AXES_ENABLED = True

# ---------------------------------------------------------------------------
# Logging – show all SQL queries in console (optional, noisy)
# ---------------------------------------------------------------------------
# Uncomment to see SQL:
# LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
#     "handlers": ["console"],
#     "level": "DEBUG",
#     "propagate": False,
# }
