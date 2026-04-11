"""
Notifications services — Email and SMS abstractions.

Uses Django's email backend for emails and a pluggable SMS provider.
Both log all outbound messages to NotificationLog for audit.
"""

import logging
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


class NotificationService:
    """Abstracted notification service for email and SMS."""

    @staticmethod
    def send_email(workspace, recipient, subject, message, related_installment=None):
        """
        Send an email notification and log it.

        Uses Django's configured EMAIL_BACKEND (console in dev, SMTP/SES in prod).
        """
        log = NotificationLog.objects.create(
            workspace=workspace,
            notification_type=NotificationLog.NotificationType.EMAIL,
            recipient=recipient,
            subject=subject,
            message=message,
            related_installment=related_installment,
        )

        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            log.status = NotificationLog.Status.SENT
            log.sent_at = timezone.now()
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            log.status = NotificationLog.Status.FAILED
            log.error_message = str(e)

        log.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
        return log

    @staticmethod
    def send_sms(workspace, recipient, message, related_installment=None):
        """
        Send an SMS notification and log it.

        Uses the configured SMS_PROVIDER. In development, logs to console.
        """
        log = NotificationLog.objects.create(
            workspace=workspace,
            notification_type=NotificationLog.NotificationType.SMS,
            recipient=recipient,
            message=message,
            related_installment=related_installment,
        )

        try:
            if settings.SMS_PROVIDER == "console":
                logger.info(f"[SMS → {recipient}] {message}")
            else:
                # Plug in real SMS provider here (Twilio, Termii, etc.)
                # Example: sms_client.send(to=recipient, body=message)
                logger.info(f"[SMS → {recipient}] Sent via {settings.SMS_PROVIDER}")

            log.status = NotificationLog.Status.SENT
            log.sent_at = timezone.now()
        except Exception as e:
            logger.error(f"SMS send failed: {e}")
            log.status = NotificationLog.Status.FAILED
            log.error_message = str(e)

        log.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
        return log

    @staticmethod
    def send_payment_confirmation(payment):
        """Send payment confirmation to the customer."""
        installment = payment.installment
        subscription = installment.subscription
        customer = subscription.customer
        workspace = payment.workspace

        subject = f"Payment Confirmed — {subscription.property.name}"
        message = (
            f"Dear {customer.full_name},\n\n"
            f"Your payment of ₦{payment.amount:,.2f} for "
            f"{subscription.property.name} (Installment #{installment.installment_number}) "
            f"has been approved.\n\n"
            f"Transaction Reference: {payment.transaction_reference}\n"
            f"Amount Paid So Far: ₦{subscription.amount_paid:,.2f}\n"
            f"Outstanding Balance: ₦{subscription.balance:,.2f}\n\n"
            f"Thank you for your payment.\n\n"
            f"— {workspace.name}"
        )

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=message,
                related_installment=installment,
            )

        if customer.phone:
            sms_message = (
                f"Payment of ₦{payment.amount:,.2f} for {subscription.property.name} "
                f"confirmed. Ref: {payment.transaction_reference}. "
                f"Balance: ₦{subscription.balance:,.2f}"
            )
            NotificationService.send_sms(
                workspace=workspace,
                recipient=customer.phone,
                message=sms_message,
                related_installment=installment,
            )

    @staticmethod
    def send_payment_rejection(payment, reason=""):
        """Send payment rejection notification."""
        installment = payment.installment
        subscription = installment.subscription
        customer = subscription.customer
        workspace = payment.workspace

        subject = f"Payment Rejected — {subscription.property.name}"
        reason_text = f"\nReason: {reason}" if reason else ""
        message = (
            f"Dear {customer.full_name},\n\n"
            f"Your payment of ₦{payment.amount:,.2f} for "
            f"{subscription.property.name} (Installment #{installment.installment_number}) "
            f"has been rejected.{reason_text}\n\n"
            f"Please resubmit a valid payment.\n\n"
            f"— {workspace.name}"
        )

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=message,
                related_installment=installment,
            )

    @staticmethod
    def send_installment_reminder(installment, days_offset):
        """
        Send installment reminder to the customer.

        Args:
            installment: Installment instance
            days_offset: Positive = before due date, negative = after
        """
        subscription = installment.subscription
        customer = subscription.customer
        workspace = subscription.workspace

        if days_offset > 0:
            timing = f"in {days_offset} day(s)"
        elif days_offset == 0:
            timing = "today"
        else:
            timing = f"{abs(days_offset)} day(s) ago (OVERDUE)"

        subject = f"Payment Reminder — {subscription.property.name}"
        message = (
            f"Dear {customer.full_name},\n\n"
            f"This is a reminder that your installment payment of "
            f"₦{installment.amount:,.2f} for {subscription.property.name} "
            f"is due {timing}.\n\n"
            f"Installment #{installment.installment_number}\n"
            f"Due Date: {installment.due_date}\n"
            f"Amount: ₦{installment.amount:,.2f}\n\n"
            f"Please make your payment promptly to avoid penalties.\n\n"
            f"— {workspace.name}"
        )

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=message,
                related_installment=installment,
            )

        if customer.phone:
            sms_message = (
                f"Reminder: ₦{installment.amount:,.2f} due {timing} for "
                f"{subscription.property.name}. Please pay on time."
            )
            NotificationService.send_sms(
                workspace=workspace,
                recipient=customer.phone,
                message=sms_message,
                related_installment=installment,
            )
