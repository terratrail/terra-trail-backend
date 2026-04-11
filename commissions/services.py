"""
Commissions services — Commission calculation and processing.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction

from commissions.models import Commission, SalesRep
from core.utils import round_currency


class CommissionService:
    """Handles commission calculation and payout management."""

    @staticmethod
    def process_payment_commission(payment):
        """
        Check if the payment's subscription was referred and create commission.

        Called automatically during payment approval.
        """
        installment = payment.installment
        subscription = installment.subscription
        customer = subscription.customer
        workspace = payment.workspace

        referral_code = customer.referral_code
        if not referral_code:
            return None

        # Find the sales rep by referral code
        try:
            sales_rep = SalesRep.objects.get(
                workspace=workspace,
                referral_code=referral_code,
                is_active=True,
            )
        except SalesRep.DoesNotExist:
            return None

        # Calculate commission
        commission_amount = CommissionService.calculate_commission(
            payment.amount, sales_rep
        )

        if commission_amount <= 0:
            return None

        commission = Commission.objects.create(
            workspace=workspace,
            sales_rep=sales_rep,
            payment=payment,
            amount=commission_amount,
            status=Commission.Status.PENDING,
        )

        return commission

    @staticmethod
    def calculate_commission(payment_amount, sales_rep):
        """
        Calculate commission based on rep's configuration.

        PERCENT: commission = payment_amount * (rate / 100)
        FIXED:   commission = rate (per payment)
        """
        if sales_rep.commission_type == "PERCENT":
            amount = payment_amount * (sales_rep.commission_rate / Decimal("100"))
        else:
            amount = sales_rep.commission_rate

        return round_currency(amount)

    @staticmethod
    @transaction.atomic
    def mark_as_paid(commission, notes=""):
        """Mark a pending commission as paid."""
        if commission.status != Commission.Status.PENDING:
            raise ValueError("Only pending commissions can be marked as paid.")

        commission.status = Commission.Status.PAID
        commission.paid_date = date.today()
        commission.notes = notes
        commission.save(update_fields=["status", "paid_date", "notes", "updated_at"])
        return commission

    @staticmethod
    def get_rep_summary(sales_rep):
        """Get commission summary for a sales rep."""
        commissions = sales_rep.commissions.all()
        return {
            "total_earned": sum(c.amount for c in commissions),
            "total_pending": sum(
                c.amount for c in commissions if c.status == Commission.Status.PENDING
            ),
            "total_paid": sum(
                c.amount for c in commissions if c.status == Commission.Status.PAID
            ),
            "commission_count": commissions.count(),
        }
