"""
Customers models — Customer, Subscription, Installment, CustomerPortalSession.

The installment schedule is generated on subscription creation via the
service layer. Installment statuses drive the reminder engine and
payment flow.
"""

import secrets
from datetime import timedelta
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from core.models import TimeStampedModel, WorkspaceScopedModel
from properties.models import PricingPlan, Property


class Customer(WorkspaceScopedModel):
    """
    A customer/buyer within a workspace.

    Customers are workspace-scoped and can have multiple subscriptions.
    """

    class ReferralSource(models.TextChoices):
        WALK_IN = "WALK_IN", "Walk-in"
        REFERRAL = "REFERRAL", "Referral"
        SOCIAL_MEDIA = "SOCIAL_MEDIA", "Social Media"
        WEBSITE = "WEBSITE", "Website"
        AGENT = "AGENT", "Agent"
        OTHER = "OTHER", "Other"

    full_name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, default="")

    # Next of Kin
    next_of_kin_name = models.CharField(max_length=255, blank=True, default="")
    next_of_kin_phone = models.CharField(max_length=20, blank=True, default="")
    next_of_kin_relationship = models.CharField(max_length=50, blank=True, default="")

    referral_source = models.CharField(
        max_length=20,
        choices=ReferralSource.choices,
        default=ReferralSource.WALK_IN,
    )
    referral_code = models.CharField(
        max_length=50, blank=True, default="",
        help_text="Sales rep referral code, if applicable",
    )
    assigned_rep = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_customers",
    )

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "email"]),
            models.Index(fields=["workspace", "phone"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"


class Subscription(WorkspaceScopedModel):
    """
    A customer's subscription to a specific property pricing plan.

    Tracks total price, amount paid, balance, and status.
    The installment schedule is generated when the subscription is created.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DEFAULTED = "DEFAULTED", "Defaulted"

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    pricing_plan = models.ForeignKey(
        PricingPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    amount_paid = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
    )
    balance = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    start_date = models.DateField(null=True, blank=True)
    estimated_end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    assigned_rep = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_subscriptions",
    )

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["customer"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name} → {self.property.name} ({self.status})"

    def update_balance(self):
        """Recalculate balance from total_price - amount_paid."""
        self.balance = self.total_price - self.amount_paid
        if self.balance <= 0:
            self.balance = Decimal("0.00")
            self.status = self.Status.COMPLETED
        self.save(update_fields=["balance", "status", "updated_at"])


class Installment(WorkspaceScopedModel):
    """
    A single installment in a subscription's payment schedule.

    Status flow:
        UPCOMING → DUE → OVERDUE (if unpaid past due_date)
        UPCOMING/DUE → PENDING (payment recorded, awaiting approval)
        PENDING → PAID (payment approved)
        PENDING → DUE (payment rejected, re-enable for payment)
    """

    class Status(models.TextChoices):
        UPCOMING = "UPCOMING", "Upcoming"
        DUE = "DUE", "Due"
        OVERDUE = "OVERDUE", "Overdue"
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="installments",
    )
    installment_number = models.PositiveIntegerField()
    due_date = models.DateField(db_index=True)
    amount = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
    )
    paid_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["installment_number"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["subscription", "installment_number"]),
        ]

    def __str__(self):
        return (
            f"#{self.installment_number} — {self.subscription.customer.full_name} "
            f"— ₦{self.amount} ({self.status})"
        )


class CustomerPortalSession(TimeStampedModel):
    """
    Token-based session for the customer self-service portal.

    Customers authenticate via OTP (email + phone matched against the
    Customer model). On success a 30-minute session token is issued.
    The token is sent in the Authorization header as:
        Authorization: PortalToken <token>
    """

    SESSION_MINUTES = 30

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="portal_sessions",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["token", "is_active"]),
        ]

    def __str__(self):
        return f"PortalSession({self.customer.email})"

    @classmethod
    def create_for_customer(cls, customer):
        token = secrets.token_urlsafe(48)
        expires_at = timezone.now() + timedelta(minutes=cls.SESSION_MINUTES)
        return cls.objects.create(customer=customer, token=token, expires_at=expires_at)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

# Re-export SiteInspection so it lives under this app's models namespace
from customers.site_inspection_models import SiteInspection  # noqa: F401,E402
