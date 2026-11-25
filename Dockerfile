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
    SECRET_KEY=build-only-placeholder \
    DB_PASSWORD=build-only \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Non-root user for security
RUN addgroup --system app && \
    adduser --system --ingroup app app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Start Gunicorn
CMD ["gunicorn", \
     "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
