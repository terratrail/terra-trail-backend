"""
Core tasks — Celery tasks for workspace housekeeping.
"""

from celery import shared_task
from django.utils import timezone

import logging

logger = logging.getLogger("terratrail")


@shared_task(name="core.tasks.purge_expired_invitations")
def purge_expired_invitations():
    """
    Daily task: Delete workspace invitations that have expired and were never accepted.

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
