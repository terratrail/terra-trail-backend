"""
Core tasks — Celery tasks for workspace housekeeping.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="core.tasks.purge_expired_invitations")
def purge_expired_invitations():
    """
    Daily task: delete workspace invitations that have expired and were never accepted.

    Expired invitations accumulate silently — this keeps the table clean and
    prevents stale tokens from being confused with valid ones during debugging.
    """
    from core.models import WorkspaceInvitation

    deleted_count, _ = WorkspaceInvitation.objects.filter(
        expires_at__lt=timezone.now(),
        is_accepted=False,
    ).delete()

    logger.info(f"Purged {deleted_count} expired workspace invitation(s).")
    return f"Purged {deleted_count} expired invitation(s)."


@shared_task(name="core.tasks.check_expiring_plans")
def check_expiring_plans():
    """
    Daily task: email workspace owners whose paid plan expires within 7 days.

    Only checks STARTER / GROWTH / SCALE plans — FREE and ENTERPRISE are
    excluded (FREE has no expiry, ENTERPRISE is managed manually).
    """
    from datetime import timedelta
    from core.models import Workspace
    from accounts.models import WorkspaceMembership
    from notifications.services import NotificationService
    from terratrail.config import settings as app_settings

    now = timezone.now()
    threshold = now + timedelta(days=7)

    expiring = Workspace.objects.filter(
        is_active=True,
        billing_plan__in=["STARTER", "GROWTH", "SCALE"],
        plan_expires_at__isnull=False,
        plan_expires_at__gt=now,
        plan_expires_at__lte=threshold,
    )

    reminder_count = 0
    for workspace in expiring:
        days_left = max((workspace.plan_expires_at - now).days, 0)
        expiry_date = workspace.plan_expires_at.strftime("%B %d, %Y")

        owners = (
            WorkspaceMembership.objects.filter(
                workspace=workspace,
                role=WorkspaceMembership.Role.OWNER,
                is_active=True,
            )
            .select_related("user")
        )

        for membership in owners:
            user = membership.user
            if not user.email:
                continue

            subject = (
                f"Your {workspace.billing_plan.capitalize()} plan expires "
                f"in {days_left} day(s) — {workspace.name}"
            )
            message = (
                f"Hi {user.full_name},\n\n"
                f"Your {workspace.billing_plan} plan for workspace '{workspace.name}' "
                f"expires in {days_left} day(s) on {expiry_date}.\n\n"
                f"To keep uninterrupted access to all features, please renew before "
                f"the expiry date.\n\n"
                f"To renew, contact us at {app_settings.BILLING_EMAIL} or transfer "
                f"your subscription fee to the account on file and send proof of "
                f"payment to {app_settings.BILLING_EMAIL}.\n\n"
                f"If you have already renewed, please disregard this message.\n\n"
                f"— The {app_settings.COMPANY_NAME} Team"
            )

            NotificationService.send_email(
                workspace=workspace,
                recipient=user.email,
                subject=subject,
                message=message,
            )
            reminder_count += 1

    logger.info(f"Sent {reminder_count} plan expiry reminder(s).")
    return f"Sent {reminder_count} plan expiry reminder(s)."
