"""
Management command: mark subscriptions as DEFAULTING when they have
installments that have been overdue for 2+ days.

Run via: python manage.py mark_defaulting
Schedule via cron or Celery Beat for daily execution.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from customers.models import Installment, Subscription


class Command(BaseCommand):
    help = "Mark active subscriptions as DEFAULTING when they have installments overdue 2+ days."

    def handle(self, *args, **options):
        cutoff = timezone.now().date() - timedelta(days=2)

        overdue_sub_ids = (
            Installment.objects.filter(
                status=Installment.Status.OVERDUE,
                due_date__lte=cutoff,
            )
            .values_list("subscription_id", flat=True)
            .distinct()
        )

        updated = Subscription.objects.filter(
            id__in=overdue_sub_ids,
            status=Subscription.Status.ACTIVE,
        ).update(status=Subscription.Status.DEFAULTING)

        self.stdout.write(
            self.style.SUCCESS(f"Marked {updated} subscription(s) as DEFAULTING.")
        )
