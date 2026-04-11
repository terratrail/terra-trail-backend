"""
Customers services — Subscription creation and installment schedule generation.

This is the heart of the scheduling logic. Two spread modes are supported:

1. INITIAL_SEPARATE:
   - Installment #1 = initial payment (due immediately)
   - Installments #2 to #(N+1) = monthly installments

2. INITIAL_AS_FIRST:
   - Installment #1 = initial payment (counts as first month)
   - Installments #2 to #N = remaining monthly installments
"""

from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from customers.models import Customer, Installment, Subscription
from properties.models import PricingPlan
from properties.services import PricingPlanService
from core.utils import round_currency


class SubscriptionService:
    """Handles subscription creation with installment schedule generation."""

    @staticmethod
    @transaction.atomic
    def create_subscription(workspace, customer, property_obj, pricing_plan, start_date=None, notes=""):
        """
        Create a subscription and generate the full installment schedule.

        Args:
            workspace: The workspace context
            customer: Customer instance
            property_obj: Property instance
            pricing_plan: PricingPlan instance
            start_date: Optional start date (defaults to today)
            notes: Optional notes

        Returns:
            Subscription instance with generated installments
        """
        if not start_date:
            start_date = date.today()

        # Lock the pricing plan's spread method
        PricingPlanService.lock_plan(pricing_plan)

        # Create subscription
        subscription = Subscription.objects.create(
            workspace=workspace,
            customer=customer,
            property=property_obj,
            pricing_plan=pricing_plan,
            total_price=pricing_plan.total_price,
            balance=pricing_plan.total_price,
            status=Subscription.Status.PENDING,
            start_date=start_date,
            notes=notes,
        )

        # Generate installment schedule
        installments = ScheduleService.generate_schedule(
            subscription=subscription,
            pricing_plan=pricing_plan,
            start_date=start_date,
        )

        # Estimate end date
        if installments:
            subscription.estimated_end_date = installments[-1].due_date
            subscription.save(update_fields=["estimated_end_date"])

        return subscription

    @staticmethod
    @transaction.atomic
    def regenerate_schedule(subscription, new_start_date=None):
        """
        Regenerate the installment schedule (e.g., after initial payment approval).

        Deletes unpaid installments and regenerates from the new start date.
        """
        # Only delete non-paid installments
        subscription.installments.exclude(status=Installment.Status.PAID).delete()

        start_date = new_start_date or subscription.start_date or date.today()
        paid_count = subscription.installments.filter(status=Installment.Status.PAID).count()

        installments = ScheduleService.generate_schedule(
            subscription=subscription,
            pricing_plan=subscription.pricing_plan,
            start_date=start_date,
            starting_number=paid_count + 1,
            skip_initial=(paid_count > 0),
        )

        if installments:
            subscription.estimated_end_date = installments[-1].due_date
            subscription.save(update_fields=["estimated_end_date"])

        return subscription


class ScheduleService:
    """Generates installment schedules based on pricing plan configuration."""

    @staticmethod
    def generate_schedule(subscription, pricing_plan, start_date, starting_number=1, skip_initial=False):
        """
        Generate installment records for a subscription.

        Returns:
            list[Installment]: Created installment instances
        """
        installments = []
        workspace = subscription.workspace

        if pricing_plan.payment_type == PricingPlan.PaymentType.OUTRIGHT:
            # Outright: Single installment for full price
            installment = Installment.objects.create(
                workspace=workspace,
                subscription=subscription,
                installment_number=starting_number,
                due_date=start_date,
                amount=pricing_plan.total_price,
                status=Installment.Status.DUE,
            )
            return [installment]

        # Installment plan
        initial = pricing_plan.initial_payment
        monthly = pricing_plan.monthly_installment
        duration = pricing_plan.duration_months
        spread = pricing_plan.payment_spread_method

        current_number = starting_number
        current_date = start_date

        if spread == PricingPlan.SpreadMethod.INITIAL_SEPARATE:
            # Mode 1: Initial payment is separate from monthly schedule
            if not skip_initial and initial > 0:
                installments.append(
                    Installment(
                        workspace=workspace,
                        subscription=subscription,
                        installment_number=current_number,
                        due_date=current_date,
                        amount=initial,
                        status=Installment.Status.DUE,
                    )
                )
                current_number += 1

            # Monthly installments
            remaining_balance = pricing_plan.total_price - initial
            for i in range(duration):
                month_date = current_date + relativedelta(months=i + (0 if skip_initial else 1))
                amount = monthly

                # Last installment: adjust for rounding
                if i == duration - 1:
                    paid_so_far = initial + (monthly * (duration - 1))
                    amount = pricing_plan.total_price - paid_so_far
                    amount = max(amount, Decimal("0.01"))

                installments.append(
                    Installment(
                        workspace=workspace,
                        subscription=subscription,
                        installment_number=current_number,
                        due_date=month_date,
                        amount=round_currency(amount),
                        status=Installment.Status.UPCOMING,
                    )
                )
                current_number += 1

        else:
            # Mode 2: Initial payment counts as first month
            if not skip_initial and initial > 0:
                installments.append(
                    Installment(
                        workspace=workspace,
                        subscription=subscription,
                        installment_number=current_number,
                        due_date=current_date,
                        amount=initial,
                        status=Installment.Status.DUE,
                    )
                )
                current_number += 1

            # Remaining months (duration - 1, since initial counts as month 1)
            remaining_months = max(duration - 1, 1)
            remaining_balance = pricing_plan.total_price - initial

            for i in range(remaining_months):
                month_date = current_date + relativedelta(months=i + 1)
                amount = monthly

                # Last installment: adjust for rounding
                if i == remaining_months - 1:
                    paid_so_far = initial + (monthly * (remaining_months - 1))
                    amount = pricing_plan.total_price - paid_so_far
                    amount = max(amount, Decimal("0.01"))

                installments.append(
                    Installment(
                        workspace=workspace,
                        subscription=subscription,
                        installment_number=current_number,
                        due_date=month_date,
                        amount=round_currency(amount),
                        status=Installment.Status.UPCOMING,
                    )
                )
                current_number += 1

        # Bulk create for efficiency
        Installment.objects.bulk_create(installments)

        # Set first upcoming installment to DUE (if initial was already set)
        first_upcoming = (
            subscription.installments
            .filter(status=Installment.Status.UPCOMING)
            .order_by("installment_number")
            .first()
        )
        if first_upcoming and not installments[0].status == Installment.Status.DUE:
            first_upcoming.status = Installment.Status.DUE
            first_upcoming.save(update_fields=["status"])

        return list(subscription.installments.order_by("installment_number"))

    @staticmethod
    def get_estimated_end_date(start_date, pricing_plan):
        """Calculate the estimated final payment date."""
        if pricing_plan.payment_type == PricingPlan.PaymentType.OUTRIGHT:
            return start_date

        duration = pricing_plan.duration_months
        if pricing_plan.payment_spread_method == PricingPlan.SpreadMethod.INITIAL_SEPARATE:
            return start_date + relativedelta(months=duration)
        else:
            return start_date + relativedelta(months=duration - 1)
