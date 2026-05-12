"""
Commissions models — SalesRep and Commission tracking.

Commission is triggered on payment approval. Each sales rep has a tier
that determines their commission rate (percentage or fixed).
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import WorkspaceScopedModel
from payments.models import Payment


class SalesRep(WorkspaceScopedModel):
    """
    A sales representative who earns commission on referred sales.

    Each rep has a unique referral code within their workspace.
    """

    class Tier(models.TextChoices):
        STARTER = "STARTER", "Starter"
        SENIOR = "SENIOR", "Senior"
        LEGEND = "LEGEND", "Legend"

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    tier = models.CharField(
        max_length=20,
        choices=Tier.choices,
        default=Tier.STARTER,
    )
    referral_code = models.CharField(max_length=50, db_index=True)

    # Commission rate configuration
    commission_type = models.CharField(
        max_length=10,
        choices=[("PERCENT", "Percentage"), ("FIXED", "Fixed Amount")],
        default="PERCENT",
    )
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Percentage (0-100) or fixed amount per payment",
    )
    is_active = models.BooleanField(default=True)

    # Contact / payout details
    address = models.TextField(blank=True, default="")
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_account_number = models.CharField(max_length=20, blank=True, default="")
    bank_account_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ["workspace", "referral_code"]
        indexes = [
            models.Index(fields=["workspace", "referral_code"]),
            models.Index(fields=["workspace", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.tier}) — {self.referral_code}"


class Commission(WorkspaceScopedModel):
    """
    Commission payout record.

    Created automatically when a payment is approved for a referral-based
    subscription. Status starts as PENDING and moves to PAID when disbursed.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    sales_rep = models.ForeignKey(
        SalesRep,
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name="commissions",
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["sales_rep"]),
        ]

    def __str__(self):
        return f"Commission for {self.sales_rep.name} — ₦{self.amount} ({self.status})"
