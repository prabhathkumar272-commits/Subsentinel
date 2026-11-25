"""
Celery configuration for the SubSentinel project.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("subsentinel")

# Read config from Django settings, using the CELERY_ namespace
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Celery Beat – periodic task schedule
# ---------------------------------------------------------------------------
app.conf.beat_schedule = {
    "check-upcoming-renewals-daily": {
        "task": "apps.notifications.tasks.check_upcoming_renewals",
        "schedule": crontab(hour=8, minute=0),  # Every day at 08:00 UTC
        "options": {"queue": "default"},
    },
    "advance-billing-dates-daily": {
        "task": "apps.notifications.tasks.advance_billing_dates",
        "schedule": crontab(hour=0, minute=30),  # Every day at 00:30 UTC
        "options": {"queue": "default"},
    },
    "check-expiring-trials-daily": {
        "task": "apps.notifications.tasks.check_expiring_trials",
        "schedule": crontab(hour=8, minute=15),  # Every day at 08:15 UTC
        "options": {"queue": "default"},
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for verifying Celery is operational."""
    print(f"Request: {self.request!r}")
