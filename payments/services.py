"""
Payments services — Payment recording, approval, and rejection logic.

The payment approval pipeline:
1. Record payment → Installment status = PENDING
2. Approve payment → Installment = PAID, update subscription balance,
                      trigger commission, trigger notifications,
                      activate next installment
3. Reject payment → Installment reverts to DUE/OVERDUE, resume reminders
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.utils import generate_reference
from customers.models import Installment, Subscription
from payments.models import Payment


class PaymentService:
    """Handles the full payment lifecycle."""

    @staticmethod
    @transaction.atomic
    def record_payment(workspace, installment, amount, recorded_by=None, receipt_url="", receipt_file=None, notes=""):
        """
        Record a new payment against an installment.

        Sets installment status to PENDING and creates a Payment record.
        """
        if installment.status == Installment.Status.PAID:
            raise ValueError("This installment is already paid.")

        if installment.status == Installment.Status.PENDING:
            raise ValueError("A payment is already pending for this installment.")

        payment = Payment.objects.create(
            workspace=workspace,
            installment=installment,
            amount=amount,
            recorded_by=recorded_by,
            receipt_url=receipt_url,
            receipt_file=receipt_file,
            transaction_reference=generate_reference("PAY"),
            notes=notes,
            status=Payment.Status.PENDING,
        )

        # Mark installment as pending
        installment.status = Installment.Status.PENDING
        installment.save(update_fields=["status", "updated_at"])

        return payment

    @staticmethod
    @transaction.atomic
    def approve_payment(payment, approved_by):
        """
        Approve a pending payment.

        Side effects:
        1. Mark installment as PAID
        2. Update subscription balance (amount_paid, balance)
        3. Activate the next installment
        4. Trigger commission calculation (via commissions app)
        5. Trigger notifications (via notifications app)
        """
        if payment.status != Payment.Status.PENDING:
            raise ValueError("Only pending payments can be approved.")

        # 1. Update payment
        payment.status = Payment.Status.APPROVED
        payment.approved_by = approved_by
        payment.save(update_fields=["status", "approved_by", "updated_at"])

        # 2. Mark installment as PAID
        installment = payment.installment
        installment.status = Installment.Status.PAID
        installment.paid_date = date.today()
        installment.save(update_fields=["status", "paid_date", "updated_at"])

        # 3. Update subscription
        subscription = installment.subscription
        subscription.amount_paid += payment.amount
        subscription.balance = subscription.total_price - subscription.amount_paid
        if subscription.balance <= 0:
            subscription.balance = Decimal("0.00")
            subscription.status = Subscription.Status.COMPLETED
        elif subscription.status == Subscription.Status.PENDING:
            subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["amount_paid", "balance", "status", "updated_at"])

        # 4. Activate next installment
        PaymentService._activate_next_installment(subscription)

        # 5. Trigger commission (deferred import to avoid circular)
        try:
            from commissions.services import CommissionService
            CommissionService.process_payment_commission(payment)
        except ImportError:
            pass

        # 6. Trigger notification (deferred import)
        try:
            from notifications.services import NotificationService
            NotificationService.send_payment_confirmation(payment)
        except ImportError:
            pass

        return payment

    @staticmethod
    @transaction.atomic
    def reject_payment(payment, reason=""):
        """
        Reject a pending payment.

        Reverts the installment status so the customer can retry payment.
        """
        if payment.status != Payment.Status.PENDING:
            raise ValueError("Only pending payments can be rejected.")

        payment.status = Payment.Status.REJECTED
        payment.notes = f"{payment.notes}\nRejection reason: {reason}".strip()
        payment.save(update_fields=["status", "notes", "updated_at"])

        # Revert installment status
        installment = payment.installment
        if installment.due_date < date.today():
            installment.status = Installment.Status.OVERDUE
        else:
            installment.status = Installment.Status.DUE
        installment.save(update_fields=["status", "updated_at"])

        # Send rejection notification
        try:
            from notifications.services import NotificationService
            NotificationService.send_payment_rejection(payment, reason)
        except ImportError:
            pass

        return payment

    @staticmethod
    def _activate_next_installment(subscription):
        """Set the next UPCOMING installment to DUE."""
        next_installment = (
            subscription.installments
            .filter(status=Installment.Status.UPCOMING)
            .order_by("installment_number")
            .first()
        )
        if next_installment:
            next_installment.status = Installment.Status.DUE
            next_installment.save(update_fields=["status", "updated_at"])
