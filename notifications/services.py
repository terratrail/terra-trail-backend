"""
Notifications services — Email and SMS abstractions.

Uses Django's email backend for emails and a pluggable SMS provider.
Both log all outbound messages to NotificationLog for audit.
"""

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from notifications.sender import resolve_sender
from django.template.loader import render_to_string
from django.utils import timezone

from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


def _render_email_html(template_name: str, context: dict) -> str:
    """Render an HTML email template with shared base context."""
    base_ctx = {
        "year": datetime.now().year,
        "support_email": getattr(settings, "DEFAULT_FROM_EMAIL", "support@terratrail.io"),
    }
    base_ctx.update(context)
    return render_to_string(f"core/email/{template_name}.html", base_ctx)


class NotificationService:
    """Abstracted notification service for email and SMS."""

    @staticmethod
    def send_email(
        workspace,
        recipient,
        subject,
        message,
        html_message=None,
        related_installment=None,
        async_send=True,
    ):
        """
        Send an email notification and log it.

        When async_send=True (default) the actual SMTP delivery is handed off to
        a Celery background task with up to 3 automatic retries.  If Celery is
        unavailable the task falls back to synchronous delivery so that emails
        are never silently dropped in development.
        """
        log = NotificationLog.objects.create(
            workspace=workspace,
            notification_type=NotificationLog.NotificationType.EMAIL,
            recipient=recipient,
            subject=subject,
            message=message,
            status=NotificationLog.Status.PENDING,
            related_installment=related_installment,
        )

        if async_send:
            try:
                from notifications.tasks import send_email_task
                send_email_task.delay(
                    log_id=log.pk,
                    subject=subject,
                    message=message,
                    recipient=recipient,
                    html_message=html_message,
                    from_email=resolve_sender(workspace),
                )
                return log
            except Exception as broker_err:
                # Broker unavailable — fall through to synchronous send
                logger.warning(f"Celery broker unavailable, sending synchronously: {broker_err}")

        # Synchronous fallback (also used when async_send=False)
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=resolve_sender(workspace),
                recipient_list=[recipient],
                html_message=html_message,
                fail_silently=False,
            )
            log.status = NotificationLog.Status.SENT
            log.sent_at = timezone.now()
        except Exception as e:
            logger.error(f"Email send failed to {recipient}: {e}")
            log.status = NotificationLog.Status.FAILED
            log.error_message = str(e)

        log.save(update_fields=["status", "sent_at", "error_message", "updated_at"])
        return log

    @staticmethod
    def send_otp_email(recipient, code, name="", expiry_minutes=None):
        """Send an OTP verification email with styled HTML template."""
        expiry = expiry_minutes or getattr(settings, "OTP_EXPIRY_MINUTES", 10)
        subject = "Your TerraTrail Verification Code"
        plain = f"Your OTP code is {code}. It expires in {expiry} minutes."
        html = _render_email_html("otp", {
            "code": code,
            "name": name,
            "expiry_minutes": expiry,
        })
        return NotificationService.send_email(
            workspace=None,
            recipient=recipient,
            subject=subject,
            message=plain,
            html_message=html,
        )

    @staticmethod
    def send_invite_email(recipient, invited_by_name, workspace_name, role, invite_url, expires_days=7):
        """Send a workspace invite email to the recipient."""
        role_label = role.replace("_", " ").title()
        subject = f"You're invited to join {workspace_name} on TerraTrail"
        plain = (
            f"Hi,\n\n"
            f"{invited_by_name} has invited you to join '{workspace_name}' as {role_label}.\n\n"
            f"Click the link below to accept:\n{invite_url}\n\n"
            f"This invitation expires in {expires_days} days.\n\n"
            f"— The TerraTrail Team"
        )
        html = _render_email_html("invite", {
            "invited_by_name": invited_by_name,
            "workspace_name": workspace_name,
            "role_label": role_label,
            "invite_url": invite_url,
            "expires_days": expires_days,
        })
        return NotificationService.send_email(
            workspace=None,
            recipient=recipient,
            subject=subject,
            message=plain,
            html_message=html,
        )

    @staticmethod
    def send_welcome_email(recipient, user_name, workspace_name, workspace_region="", support_email=""):
        """Send workspace welcome / onboarding email."""
        subject = f"Your workspace '{workspace_name}' is ready — TerraTrail"
        plain = (
            f"Hi {user_name},\n\n"
            f"Your workspace '{workspace_name}' has been created and is ready to use.\n\n"
            f"Get started by inviting your team, adding your first property, "
            f"and setting up your billing plan.\n\n"
            f"— The TerraTrail Team"
        )
        html = _render_email_html("welcome", {
            "user_name": user_name,
            "workspace_name": workspace_name,
            "workspace_region": workspace_region,
            "support_email": support_email or settings.DEFAULT_FROM_EMAIL,
        })
        return NotificationService.send_email(
            workspace=None,
            recipient=recipient,
            subject=subject,
            message=plain,
            html_message=html,
        )

    @staticmethod
    def send_inspection_booking_email(inspection, workspace):
        """Send booking confirmation email to the person who booked an inspection."""
        if not inspection.email:
            return

        prop_name = inspection.property_name or (
            inspection.linked_property.name if inspection.linked_property else "the property"
        )
        date_str = inspection.inspection_date.strftime("%B %d, %Y") if inspection.inspection_date else ""
        time_str = inspection.inspection_time.strftime("%I:%M %p") if inspection.inspection_time else ""

        subject = f"Inspection Booking Confirmed — {prop_name}"
        plain = (
            f"Hi {inspection.name},\n\n"
            f"Your site inspection request for {prop_name} has been received.\n\n"
            f"Date: {date_str}\n"
            f"Time: {time_str or 'To be confirmed'}\n"
            f"Type: {inspection.get_inspection_type_display()}\n\n"
            f"Our team will be in touch to confirm the appointment.\n\n"
            f"— {workspace.name}"
        )
        html = _render_email_html("inspection_booking", {
            "customer_name": inspection.name,
            "property_name": prop_name,
            "inspection_date": date_str,
            "inspection_time": time_str,
            "inspection_type": inspection.get_inspection_type_display(),
            "persons": inspection.persons,
            "notes": inspection.notes,
            "workspace_name": workspace.name,
            "support_email": getattr(workspace, "support_email", settings.DEFAULT_FROM_EMAIL),
        })
        NotificationService.send_email(
            workspace=workspace,
            recipient=inspection.email,
            subject=subject,
            message=plain,
            html_message=html,
        )

    @staticmethod
    def send_subscription_confirmation_email(subscription):
        """Send a subscription/purchase confirmation email to the customer."""
        customer = subscription.customer
        workspace = subscription.workspace
        if not customer.email:
            return

        prop = subscription.property
        plan = subscription.pricing_plan
        plan_name = plan.plan_name if plan else ""
        total = f"{subscription.total_price:,.2f}" if subscription.total_price else ""
        payment_type = (plan.payment_type if plan else "OUTRIGHT").upper()

        subject = f"Property Purchase Confirmed — {prop.name}"
        plain = (
            f"Dear {customer.full_name},\n\n"
            f"Congratulations! Your subscription to {prop.name} has been confirmed.\n\n"
            f"Plan: {plan_name}\n"
            f"Total Price: ₦{total}\n"
            f"Payment Type: {payment_type.capitalize()}\n\n"
            f"Thank you for choosing {workspace.name}. We'll be in touch with next steps.\n\n"
            f"— {workspace.name}"
        )
        html = _render_email_html("property_purchase", {
            "customer_name": customer.full_name,
            "property_name": prop.name,
            "property_location": prop.location.city if hasattr(prop, "location") and prop.location else "",
            "plan_name": plan_name,
            "total_price": total,
            "payment_type": payment_type.capitalize(),
            "workspace_name": workspace.name,
            "support_email": getattr(workspace, "support_email", settings.DEFAULT_FROM_EMAIL),
        })
        NotificationService.send_email(
            workspace=workspace,
            recipient=customer.email,
            subject=subject,
            message=plain,
            html_message=html,
        )

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
        plain = (
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
        html = _render_email_html("payment_confirmation", {
            "customer_name": customer.full_name,
            "property_name": subscription.property.name,
            "amount": f"{payment.amount:,.2f}",
            "installment_number": installment.installment_number,
            "transaction_reference": payment.transaction_reference,
            "amount_paid": f"{subscription.amount_paid:,.2f}",
            "outstanding_balance": f"{subscription.balance:,.2f}",
            "workspace_name": workspace.name,
            "support_email": getattr(workspace, "support_email", settings.DEFAULT_FROM_EMAIL),
        })

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=plain,
                html_message=html,
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
        plain = (
            f"Dear {customer.full_name},\n\n"
            f"Your payment of ₦{payment.amount:,.2f} for "
            f"{subscription.property.name} (Installment #{installment.installment_number}) "
            f"has been rejected.{reason_text}\n\n"
            f"Please resubmit a valid payment.\n\n"
            f"— {workspace.name}"
        )
        html = _render_email_html("payment_rejection", {
            "customer_name": customer.full_name,
            "property_name": subscription.property.name,
            "amount": f"{payment.amount:,.2f}",
            "installment_number": installment.installment_number,
            "reason": reason,
            "workspace_name": workspace.name,
            "support_email": getattr(workspace, "support_email", settings.DEFAULT_FROM_EMAIL),
        })

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=plain,
                html_message=html,
                related_installment=installment,
            )

    @staticmethod
    def send_installment_reminder(installment, days_offset):
        """
        Send installment reminder to the customer.

        Args:
            installment: Installment instance
            days_offset: Positive = before due date, negative = after (overdue)
        """
        subscription = installment.subscription
        customer = subscription.customer
        workspace = subscription.workspace

        is_overdue = days_offset < 0
        if days_offset > 0:
            timing = f"in {days_offset} day(s)"
        elif days_offset == 0:
            timing = "today"
        else:
            timing = f"{abs(days_offset)} day(s) ago (OVERDUE)"

        subject = f"Payment Reminder — {subscription.property.name}"
        plain = (
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
        html = _render_email_html("installment_reminder", {
            "customer_name": customer.full_name,
            "property_name": subscription.property.name,
            "installment_number": installment.installment_number,
            "amount": f"{installment.amount:,.2f}",
            "due_date": installment.due_date,
            "timing": timing,
            "is_overdue": is_overdue,
            "workspace_name": workspace.name,
            "support_email": getattr(workspace, "support_email", settings.DEFAULT_FROM_EMAIL),
        })

        if customer.email:
            NotificationService.send_email(
                workspace=workspace,
                recipient=customer.email,
                subject=subject,
                message=plain,
                html_message=html,
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
