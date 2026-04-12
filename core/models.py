"""
Core models — Workspace and abstract base models.

Every tenant-scoped model in the system inherits from WorkspaceScopedModel,
ensuring consistent multi-tenancy enforcement at the model layer.
"""

import uuid
from django.db import models
from django.utils.text import slugify


class TimeStampedModel(models.Model):
    """Abstract base with automatic created/updated timestamps."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class Workspace(TimeStampedModel):
    """
    Represents a real estate company / tenant.

    All data in the system is scoped to a workspace.
    """

    class BillingPlan(models.TextChoices):
        FREE = "FREE", "Free"
        STARTER = "STARTER", "Starter"
        GROWTH = "GROWTH", "Growth"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    logo = models.ImageField(upload_to="workspaces/logos/", blank=True, null=True)
    
    # Regional & Behavior
    timezone = models.CharField(max_length=63, default="Africa/Lagos")
    region = models.CharField(max_length=100, default="Nigeria")
    initial_payment_as_first_month = models.BooleanField(default=False)
    create_estate_public_pages = models.BooleanField(default=True)

    # Help Center
    intercom_app_id = models.CharField(max_length=100, blank=True, default="")
    support_email = models.EmailField(blank=True, default="")
    support_whatsapp = models.CharField(max_length=20, blank=True, default="")

    # Social Links
    website_url = models.URLField(max_length=500, blank=True, default="")
    instagram_url = models.URLField(max_length=500, blank=True, default="")

    # Billing
    billing_plan = models.CharField(
        max_length=20,
        choices=BillingPlan.choices,
        default=BillingPlan.FREE
    )
    plan_expires_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["billing_plan"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            # Ensure uniqueness
            original_slug = self.slug
            counter = 1
            while Workspace.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)


class WorkspaceScopedModel(TimeStampedModel):
    """
    Abstract base for all workspace-scoped models.

    Enforces the multi-tenancy FK on every child model.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="%(class)s_set",
        db_index=True,
    )

    class Meta:
        abstract = True


class WorkspaceScopedManager(models.Manager):
    """Manager that filters querysets by workspace."""

    def for_workspace(self, workspace):
        return self.get_queryset().filter(workspace=workspace)


class WorkspaceSettings(WorkspaceScopedModel):
    """
    Granular permission settings for a workspace.
    Controls role behavior (e.g. what Customer Reps can do).
    """

    # Customer Rep Permissions
    can_reps_approve_bookings = models.BooleanField(default=False)
    can_reps_manage_subscriptions = models.BooleanField(
        default=False, 
        help_text="Requires can_reps_approve_bookings to be True"
    )
    can_reps_manage_sales_reps = models.BooleanField(default=False)
    
    # Notification Toggles
    notify_customer_on_booking_status = models.BooleanField(default=True)
    notify_admin_on_new_booking = models.BooleanField(default=True)
    notify_customer_on_payment_receipt = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Workspace Settings"

    def __str__(self):
        return f"Settings for {self.workspace.name}"


class WorkspaceActivity(WorkspaceScopedModel):
    """
    Audit log for actions within a workspace.
    """

    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="workspace_activities",
    )
    action_text = models.CharField(max_length=500)
    category = models.CharField(
        max_length=100, 
        default="General",
        help_text="e.g. Workspace, Billing, Customer, Property"
    )
    link = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        verbose_name_plural = "Workspace Activities"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.actor} - {self.action_text}"


class WorkspaceInvitation(WorkspaceScopedModel):
    """
    Invitations to join a workspace.
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        SALES_REP = "SALES_REP", "Sales Rep"

    email = models.EmailField()
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )
    token = models.CharField(max_length=100, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_invites",
    )
    expires_at = models.DateTimeField()
    is_accepted = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Workspace Invitations"

    def __str__(self):
        return f"Invite for {self.email} as {self.role}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
