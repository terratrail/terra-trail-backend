"""
Notifications models — NotificationLog.

Tracks all outbound notifications (email, SMS) for audit and debugging.
"""

from django.db import models
from core.models import WorkspaceScopedModel


class NotificationLog(WorkspaceScopedModel):
    """
    Audit log for all notifications sent by the system.

    Captures type, recipient, content, and delivery status.
    """

    class NotificationType(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        SMS = "SMS", "SMS"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
    )
    recipient = models.CharField(
        max_length=255,
        help_text="Email address or phone number",
    )
    subject = models.CharField(max_length=255, blank=True, default="")
    message = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")

    # Optional reference to the installment this notification relates to
    related_installment = models.ForeignKey(
        "customers.Installment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="notifications",
    )

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "notification_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["sent_at"]),
        ]

    def __str__(self):
        return f"{self.notification_type} → {self.recipient} ({self.status})"
