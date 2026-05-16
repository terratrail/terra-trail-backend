"""
SiteInspection model — tracks inspection request from prospective buyers.
"""

from django.db import models
from core.models import WorkspaceScopedModel
from properties.models import Property


class SiteInspection(WorkspaceScopedModel):
    """A site inspection request for a property."""

    class InspectionType(models.TextChoices):
        PHYSICAL = "PHYSICAL", "Physical"
        VIRTUAL = "VIRTUAL", "Virtual"

    class Category(models.TextChoices):
        RESIDENTIAL = "RESIDENTIAL", "Residential"
        COMMERCIAL = "COMMERCIAL", "Commercial"
        FARM_LAND = "FARM_LAND", "Farm Land"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ATTENDED = "ATTENDED", "Attended"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No Show"

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY", "Prefer not to say"

    class CustomerType(models.TextChoices):
        EXISTING = "EXISTING", "Existing Customer"
        NEW = "NEW", "New Customer"

    # Contact info
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        blank=True,
        default="",
    )
    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
        blank=True,
        default="",
        help_text="Auto-set on creation: EXISTING if email matches a customer, else NEW.",
    )

    # Property (optional FK — can be free-text if property not yet listed)
    linked_property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_inspections",
    )
    property_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Free-text fallback when no FK property is linked.",
    )

    # Schedule
    inspection_date = models.DateField()
    inspection_time = models.TimeField(null=True, blank=True)

    # Metadata
    inspection_type = models.CharField(
        max_length=20,
        choices=InspectionType.choices,
        default=InspectionType.PHYSICAL,
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.RESIDENTIAL,
    )
    persons = models.PositiveSmallIntegerField(default=1)
    attendees = models.JSONField(
        default=list,
        blank=True,
        help_text='List of attendees: [{"name": "...", "phone": "...", "email": "..."}]',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.TextField(blank=True, default="")
    assigned_rep = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_inspections",
    )
    converted_customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_inspections",
    )

    class Meta:
        verbose_name = "Site Inspection"
        verbose_name_plural = "Site Inspections"
        ordering = ["-inspection_date", "-created_at"]
        indexes = [
            models.Index(fields=["workspace", "inspection_date"]),
            models.Index(fields=["workspace", "status"]),
        ]

    def __str__(self):
        prop = self.property.name if self.property else self.property_name
        return f"{self.name} → {prop} on {self.inspection_date}"

    @property
    def attended(self):
        return self.status == self.Status.ATTENDED
