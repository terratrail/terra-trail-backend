"""
Notifications tasks — Celery tasks for email delivery and the reminder engine.

Email tasks:
  - send_email_task: async email delivery with up to 3 retries (60s backoff)

Reminder engine runs daily and checks all installments:
  - 7 days before due date  - 2 days before due date
  - On due date
  - 2 days after due date (overdue)
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone

from customers.models import Installment

logger = logging.getLogger(__name__)


@shared_task(
    name="notifications.tasks.send_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_email_task(self, log_id, subject, message, recipient, html_message=None, from_email=None):
    """
    Background email delivery task with automatic retry on failure.
    Accepts a NotificationLog PK so it can update status after delivery.
    """
    from django.conf import settings
    from notifications.models import NotificationLog

    _from = from_email or settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=_from,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False,
        )
        NotificationLog.objects.filter(pk=log_id).update(
            status=NotificationLog.Status.SENT,
            sent_at=timezone.now(),
            error_message="",
        )
        logger.info(f"[EMAIL SENT] -> {recipient} (log {log_id})")
    except Exception as exc:
        err = str(exc)
        logger.error(f"[EMAIL FAILED] -> {recipient}: {err}")
        NotificationLog.objects.filter(pk=log_id).update(
            status=NotificationLog.Status.FAILED,
            error_message=err,
        )
        # Celery will retry automatically via autoretry_for
        raise


@shared_task(name="notifications.tasks.check_installment_reminders")
def check_installment_reminders():
    """
    Daily Celery task: Check all installments and trigger reminders.

    Runs at 8 AM UTC (configured in terratrail/celery.py).
    """
    from notifications.services import NotificationService

    today = date.today()
    reminder_days = [7, 2, 0, -2]  # Positive = before, 0 = on, negative = after

    total_sent = 0

    for days_offset in reminder_days:
        target_date = today + timedelta(days=days_offset)

        # Find installments due on the target date
        installments = Installment.objects.filter(
            due_date=target_date,
        ).exclude(
            # Suppress if already paid or payment pending
            status__in=[
                Installment.Status.PAID,
                Installment.Status.PENDING,
            ]
        ).select_related(
            "subscription__customer",
            "subscription__property",
            "workspace",
        )

        for installment in installments:
            try:
                NotificationService.send_installment_reminder(
                    installment=installment,
                    days_offset=days_offset,
                )
                total_sent += 1
            except Exception as e:
                # Log but don't fail the entire task
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    f"Failed to send reminder for installment {installment.id}: {e}"
                )

    return f"Sent {total_sent} reminder(s)."
