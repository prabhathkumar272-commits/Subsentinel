# ---------------------------------------------------------------------------
# SubSentinel – Production Dockerfile
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create required directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Collect static files
RUN DJANGO_SETTINGS_MODULE=config.settings.prod \
    SECRET_KEY=build-only-placeholder-build-only-placeholder-1234567890 \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=https://localhost \
    DB_NAME=build \
    DB_USER=build \
    DB_PASSWORD=build-only \
    DB_HOST=localhost \
    EMAIL_HOST=localhost \
    ADMIN_EMAIL=admin@localhost \
    python manage.py collectstatic --noinput

# Non-root user for security
RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Start Gunicorn
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120 --access-logfile - --error-logfile -"]
