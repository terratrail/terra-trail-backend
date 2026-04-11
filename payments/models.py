"""
Payments models — Payment records linked to installments.

Payment flow:
    Record → status=PENDING
    Approve → status=APPROVED (triggers commission, notifications)
    Reject  → status=REJECTED (re-enables installment for payment)
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator

from accounts.models import User
from core.models import WorkspaceScopedModel
from customers.models import Installment


class Payment(WorkspaceScopedModel):
    """
    A payment record against a specific installment.

    Can be recorded by admin or customer. Requires admin approval.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    installment = models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_date = models.DateField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="recorded_payments",
        help_text="Admin or customer who recorded this payment",
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="approved_payments",
    )
    receipt_url = models.URLField(blank=True, default="")
    receipt_file = models.FileField(
        upload_to="payments/receipts/", blank=True, null=True
    )
    transaction_reference = models.CharField(
        max_length=50, unique=True, db_index=True,
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["installment"]),
            models.Index(fields=["transaction_reference"]),
        ]

    def __str__(self):
        return f"Payment {self.transaction_reference} — ₦{self.amount} ({self.status})"
