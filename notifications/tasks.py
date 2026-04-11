"""
Notifications tasks — Celery tasks for the reminder engine.

The reminder engine runs daily and checks all installments:
  - 7 days before due date
  - 2 days before due date
  - On due date
  - 2 days after due date (overdue)

Suppression rules:
  - Suppress if installment status is PENDING or PAID
  - Resume reminders if payment was REJECTED
"""

from datetime import date, timedelta

from celery import shared_task
from django.db.models import Q

from customers.models import Installment


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
