"""
Production settings for SubSentinel.
"""

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug
# ---------------------------------------------------------------------------
DEBUG = False

# Production must never inherit the development fallback secret from base.py.
SECRET_KEY = config("SECRET_KEY")
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or "django-insecure-" in SECRET_KEY:
    raise ImproperlyConfigured(
        "Production SECRET_KEY must be a unique, randomly generated value of at least 50 characters."
    )

# ---------------------------------------------------------------------------
# Hosts
# ---------------------------------------------------------------------------
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# ---------------------------------------------------------------------------
# Database – PostgreSQL
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", default="5432"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
            "sslmode": config("DB_SSLMODE", default="prefer"),
        },
    }
}

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_REDIRECT_EXEMPT = [r"^health/live/$", r"^health/ready/$"]
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Email – SMTP
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
admin_email = config("ADMIN_EMAIL")
ADMINS = [("SubSentinel administrator", admin_email)]

# ---------------------------------------------------------------------------
# Static files – WhiteNoise with compression + caching
# ---------------------------------------------------------------------------
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ---------------------------------------------------------------------------
# Cache – Redis
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": config("CELERY_BROKER_URL", default="redis://localhost:6379/0"),
    }
}

# ---------------------------------------------------------------------------
# Logging – stricter in production
# ---------------------------------------------------------------------------
LOGGING["loggers"]["django"]["level"] = "WARNING"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "INFO"  # noqa: F405
LOGGING["handlers"]["console"] = {  # noqa: F405
    "class": "logging.StreamHandler",
    "level": "INFO",
    "formatter": "verbose",
}
LOGGING["loggers"]["django"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}
LOGGING["loggers"]["django.request"] = {  # noqa: F405
    "handlers": ["console", "mail_admins"],
    "level": "ERROR",
    "propagate": False,
}
LOGGING["loggers"]["apps"] = {  # noqa: F405
    "handlers": ["console", "mail_admins"],
    "level": "INFO",
    "propagate": False,
}

# ---------------------------------------------------------------------------
# CSRF trusted origins
# ---------------------------------------------------------------------------
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())
