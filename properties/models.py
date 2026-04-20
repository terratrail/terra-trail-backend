"""
Properties models — Property, PropertyLocation, PricingPlan, BankAccount.

PricingPlan contains installment calculation logic and supports two
payment spread methods:
  1. INITIAL_SEPARATE — Initial payment is separate; monthly installments
     spread over the remaining balance.
  2. INITIAL_AS_FIRST — Initial payment counts as the first month;
     remaining balance spread over (duration - 1) months.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from core.models import WorkspaceScopedModel


class Property(WorkspaceScopedModel):
    """A real estate property listed by a workspace."""

    class PropertyType(models.TextChoices):
        RESIDENTIAL_LAND = "RESIDENTIAL_LAND", "Residential Land"
        FARM_LAND = "FARM_LAND", "Farm Land"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        MIXED_USE = "MIXED_USE", "Mixed Use"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"

    name = models.CharField(max_length=255)
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.RESIDENTIAL_LAND,
    )
    description = models.TextField(blank=True, default="")
    total_sqms = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit_measurement = models.CharField(max_length=20, default="sqm")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    featured_image = models.ImageField(
        upload_to="properties/images/", blank=True, null=True
    )
    available_units = models.PositiveIntegerField(
        default=0,
        help_text="Number of plots/units available for sale",
    )

    # Commission overrides per tier — null means use workspace default
    commission_override_starter = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Override workspace default Starter tier commission % for this property.",
    )
    commission_override_senior = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Override workspace default Senior tier commission % for this property.",
    )
    commission_override_legend = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Override workspace default Legend tier commission % for this property.",
    )

    class Meta:
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["property_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.workspace.name})"


class PropertyLocation(WorkspaceScopedModel):
    """Physical location of a property."""

    property = models.OneToOneField(
        Property,
        on_delete=models.CASCADE,
        related_name="location",
    )
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, default="Nigeria")
    postal_code = models.CharField(max_length=20, blank=True, default="")
    nearest_landmark = models.CharField(max_length=255, blank=True, default="")
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    def __str__(self):
        return f"Location: {self.address}"


class PricingPlan(WorkspaceScopedModel):
    """
    Pricing plan for a property.

    Supports outright and installment payment types with two spread methods.
    The monthly_installment is computed and stored for performance.

    ⚠️ The payment_spread_method is locked after a subscription uses this plan.
    """

    class PaymentType(models.TextChoices):
        OUTRIGHT = "OUTRIGHT", "Outright"
        INSTALLMENT = "INSTALLMENT", "Installment"

    class SpreadMethod(models.TextChoices):
        INITIAL_SEPARATE = "INITIAL_SEPARATE", "Initial Separate"
        INITIAL_AS_FIRST = "INITIAL_AS_FIRST", "Initial as First Month"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="pricing_plans",
    )
    plan_name = models.CharField(max_length=255)
    land_size = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Size allocated under this plan (in sqm)",
    )
    total_price = models.DecimalField(
        max_digits=14, decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.INSTALLMENT,
    )
    initial_payment = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
        help_text="Required initial/down payment",
    )
    duration_months = models.PositiveIntegerField(
        default=12,
        help_text="Total duration in months for installment plans",
    )
    payment_spread_method = models.CharField(
        max_length=20,
        choices=SpreadMethod.choices,
        default=SpreadMethod.INITIAL_SEPARATE,
    )
    monthly_installment = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00"),
        help_text="Computed monthly installment amount (auto-calculated)",
    )
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(
        default=False,
        help_text="Locked after a subscription uses this plan",
    )

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "property"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.plan_name} — {self.property.name}"

    def save(self, *args, **kwargs):
        """Auto-calculate monthly installment before saving."""
        if self.payment_type == self.PaymentType.INSTALLMENT:
            self.monthly_installment = self.calculate_monthly_installment()
        super().save(*args, **kwargs)

    def calculate_monthly_installment(self):
        """
        Calculate the monthly installment based on the spread method.

        INITIAL_SEPARATE:
            monthly = (total_price - initial_payment) / duration_months

        INITIAL_AS_FIRST:
            monthly = (total_price - initial_payment) / (duration_months - 1)
            (initial payment counts as month 1)
        """
        if self.payment_type == self.PaymentType.OUTRIGHT:
            return Decimal("0.00")

        balance = self.total_price - self.initial_payment

        if balance <= 0:
            return Decimal("0.00")

        if self.payment_spread_method == self.SpreadMethod.INITIAL_SEPARATE:
            months = self.duration_months
        else:  # INITIAL_AS_FIRST
            months = max(self.duration_months - 1, 1)

        from core.utils import round_currency
        return round_currency(balance / months)


class BankAccount(WorkspaceScopedModel):
    """Bank account linked to a property for payment collection."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="bank_accounts",
    )
    bank_name = models.CharField(max_length=255)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "property"]),
        ]

    def __str__(self):
        return f"{self.bank_name} — {self.account_number}"


class PropertyAmenity(WorkspaceScopedModel):
    """
    An amenity offered by a property (e.g. Perimeter Fencing, Road Network).

    Tracks both the amenity name and its completion status so the workspace
    can communicate availability to potential buyers.
    """

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="amenities",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Property Amenities"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["workspace", "property"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.property.name})"


class PropertyDocument(WorkspaceScopedModel):
    """
    A legal or administrative document associated with a property
    (e.g. C of O, Deed of Assignment, Survey Plan).

    Tracks availability status so agents can show buyers what documentation
    is ready before purchase.
    """

    class DocumentType(models.TextChoices):
        C_OF_O = "C_OF_O", "Certificate of Occupancy (C of O)"
        DEED_OF_ASSIGNMENT = "DEED_OF_ASSIGNMENT", "Deed of Assignment"
        SURVEY_PLAN = "SURVEY_PLAN", "Survey Plan"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        READY = "READY", "Ready"

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    document_file = models.FileField(
        upload_to="properties/documents/",
        blank=True,
        null=True,
        help_text="Optional — upload the actual document file.",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        verbose_name_plural = "Property Documents"
        ordering = ["document_type"]
        indexes = [
            models.Index(fields=["workspace", "property"]),
        ]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.property.name}"


class PropertyGallery(WorkspaceScopedModel):
    """
    Gallery images for a property.

    The primary cover image lives on Property.featured_image.
    These are the additional gallery photos shown in the property detail page.
    """

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="gallery_images",
    )
    image = models.ImageField(upload_to="properties/gallery/")
    caption = models.CharField(max_length=255, blank=True, default="")
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order — lower numbers appear first.",
    )

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["workspace", "property"]),
        ]

    def __str__(self):
        return f"Gallery image for {self.property.name} (order {self.order})"
