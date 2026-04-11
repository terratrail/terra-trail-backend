"""
Customers tasks — Celery tasks for installment status management.
"""

from celery import shared_task
from datetime import date
from django.utils import timezone

from customers.models import Installment


@shared_task(name="customers.tasks.mark_overdue_installments")
def mark_overdue_installments():
    """
    Daily task: Mark installments past their due date as OVERDUE.

    Only transitions DUE → OVERDUE. Does not touch PENDING or PAID.
    """
    today = date.today()
    overdue_count = Installment.objects.filter(
        status=Installment.Status.DUE,
        due_date__lt=today,
    ).update(status=Installment.Status.OVERDUE)

    return f"Marked {overdue_count} installments as OVERDUE."
