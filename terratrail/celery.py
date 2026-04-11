"""
Celery configuration for TerraTrail.

This module sets up the Celery application instance and auto-discovers
tasks from all installed Django apps.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "terratrail.settings")

app = Celery("terratrail")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Periodic Tasks (Celery Beat)
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "check-installment-reminders": {
        "task": "notifications.tasks.check_installment_reminders",
        "schedule": crontab(hour=8, minute=0),  # Daily at 8 AM UTC
    },
    "mark-overdue-installments": {
        "task": "customers.tasks.mark_overdue_installments",
        "schedule": crontab(hour=0, minute=30),  # Daily at 12:30 AM UTC
    },
}
