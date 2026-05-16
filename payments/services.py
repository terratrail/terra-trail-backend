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
import logging
from payments.models import Payment

logger = logging.getLogger("terratrail")


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

        # Allow recording a new payment on a PARTIALLY_PAID installment

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

        logger.info(f"Payment recorded: {payment.transaction_reference} for installment {installment.id}")
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

        # 2. Apply payment to installment — handle under/overpayment
        installment = payment.installment
        installment_due = installment.amount
        already_paid = installment.amount_paid
        total_paid_now = already_paid + payment.amount

        if total_paid_now < installment_due:
            # Underpayment: partially paid
            installment.amount_paid = total_paid_now
            installment.status = Installment.Status.PARTIALLY_PAID
            installment.save(update_fields=["amount_paid", "status", "updated_at"])
        else:
            # Full or overpayment
            installment.amount_paid = installment_due  # cap at due amount
            installment.status = Installment.Status.PAID
            installment.paid_date = payment.payment_date or date.today()
            installment.save(update_fields=["amount_paid", "status", "paid_date", "updated_at"])

            # Handle overpayment: apply excess to subsequent installments in order
            excess = total_paid_now - installment_due
            if excess > 0:
                future_installments = Installment.objects.filter(
                    subscription=installment.subscription,
                    installment_number__gt=installment.installment_number,
                ).exclude(
                    status=Installment.Status.PAID,
                ).order_by("installment_number")

                for future_inst in future_installments:
                    if excess <= Decimal("0.00"):
                        break
                    remaining_on_inst = future_inst.amount - future_inst.amount_paid
                    if excess >= remaining_on_inst:
                        excess -= remaining_on_inst
                        future_inst.amount_paid = future_inst.amount
                        future_inst.status = Installment.Status.PAID
                        future_inst.paid_date = payment.payment_date or date.today()
                    else:
                        future_inst.amount_paid += excess
                        future_inst.status = Installment.Status.PARTIALLY_PAID
                        excess = Decimal("0.00")
                    future_inst.save(update_fields=["amount_paid", "status", "paid_date", "updated_at"])

        # 3. Update subscription totals
        subscription = installment.subscription
        subscription.amount_paid += payment.amount
        subscription.balance = subscription.total_price - subscription.amount_paid
        if subscription.balance <= 0:
            subscription.balance = Decimal("0.00")
            subscription.status = Subscription.Status.COMPLETED
        elif subscription.status == Subscription.Status.PENDING:
            subscription.status = Subscription.Status.ACTIVE
        subscription.save(update_fields=["amount_paid", "balance", "status", "updated_at"])

        # 4. Activate next installments only when the current installment is FULLY paid.
        #    For underpayments (PARTIALLY_PAID) the installment is still open — skip.
        installment_fully_paid = (installment.status == Installment.Status.PAID)
        if installment_fully_paid:
            if installment.installment_number == 1:
                # Recalculate all future due dates anchored to today (PRD 5.3.2).
                try:
                    from customers.services import SubscriptionService
                    SubscriptionService.regenerate_schedule(
                        subscription=subscription,
                        new_start_date=date.today(),
                    )
                except Exception as e:
                    logger.error(
                        f"Schedule regeneration failed for subscription "
                        f"{subscription.id}: {e}"
                    )
            else:
                # For subsequent payments, activate the next UPCOMING installment.
                PaymentService._activate_next_installment(subscription)

        # 5 & 6. Trigger commission + notification after the transaction commits.
        # Using on_commit ensures these side effects only run if the DB write
        # succeeds — a failed SMTP call can no longer roll back a valid approval.
        payment_id = payment.id

        def _post_approve():
            from payments.models import Payment as _Payment
            _payment = _Payment.objects.get(pk=payment_id)
            try:
                from commissions.services import CommissionService
                CommissionService.process_payment_commission(_payment)
            except Exception as e:
                logger.error(
                    f"Commission processing failed for payment "
                    f"{_payment.transaction_reference}: {e}"
                )
            try:
                from notifications.services import NotificationService
                NotificationService.send_payment_confirmation(_payment)
            except Exception as e:
                logger.error(
                    f"Confirmation notification failed for payment "
                    f"{_payment.transaction_reference}: {e}"
                )

        transaction.on_commit(_post_approve)

        logger.info(f"Payment approved: {payment.transaction_reference}")
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

        # Send rejection notification after the transaction commits.
        payment_id = payment.id

        def _post_reject():
            from payments.models import Payment as _Payment
            _payment = _Payment.objects.get(pk=payment_id)
            try:
                from notifications.services import NotificationService
                NotificationService.send_payment_rejection(_payment, reason)
            except Exception as e:
                logger.error(
                    f"Rejection notification failed for payment "
                    f"{_payment.transaction_reference}: {e}"
                )

        transaction.on_commit(_post_reject)

        logger.info(f"Payment rejected: {payment.transaction_reference}. Reason: {reason}")
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
