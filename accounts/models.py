"""
Accounts models — Custom User, WorkspaceMembership, OTP.

The User model uses email as the primary identifier (USERNAME_FIELD).
Workspace membership is a many-to-many through model that stores
per-workspace roles.
"""

import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel, Workspace


class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom user model — email-based authentication.

    Roles are stored per-workspace via WorkspaceMembership, but the user
    also has a `default_role` for system-level context.
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        SALES_REP = "SALES_REP", "Sales Rep"

    class Title(models.TextChoices):
        MR = "MR", "Mr."
        MRS = "MRS", "Mrs."
        MS = "MS", "Ms."
        DR = "DR", "Dr."
        CHIEF = "CHIEF", "Chief"
        PASTOR = "PASTOR", "Pastor"

    class Gender(models.TextChoices):
        MALE = "MALE", "Male"
        FEMALE = "FEMALE", "Female"
        OTHER = "OTHER", "Other"

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        MARRIED = "MARRIED", "Married"
        DIVORCED = "DIVORCED", "Divorced"
        WIDOWED = "WIDOWED", "Widowed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Remove username field
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    title = models.CharField(
        max_length=10, choices=Title.choices, blank=True, default=""
    )
    gender = models.CharField(
        max_length=10, choices=Gender.choices, blank=True, default=""
    )
    birth_month = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Birthday month (1–12)",
    )
    birth_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Birthday day (1–31)",
    )
    occupation = models.CharField(max_length=255, blank=True, default="")
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, blank=True, default=""
    )
    address = models.TextField(blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="Nigeria")
    state = models.CharField(max_length=100, blank=True, default="")
    nationality = models.CharField(max_length=100, blank=True, default="")

    default_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )
    first_name = models.CharField(max_length=150, blank=True, default="")
    last_name = models.CharField(max_length=150, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class WorkspaceMembership(TimeStampedModel):
    """
    Through model for User ↔ Workspace many-to-many relationship.

    Stores the user's role within each workspace they belong to.
    """

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        CUSTOMER = "CUSTOMER", "Customer"
        SALES_REP = "SALES_REP", "Sales Rep"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="workspace_memberships",
    )
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ADMIN,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["user", "workspace"]
        indexes = [
            models.Index(fields=["user", "workspace"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.workspace.name} ({self.role})"


class OTPToken(TimeStampedModel):
    """
    One-Time Password token for customer portal authentication.

    Rules:
    - 6-digit code
    - Expires after OTP_EXPIRY_MINUTES (default 10)
    - Max OTP_MAX_ATTEMPTS (default 3) failed attempts
    - Lockout after max attempts for OTP_LOCKOUT_MINUTES (default 15)
    """

    email = models.EmailField(db_index=True, blank=True, default="")
    phone = models.CharField(max_length=20, db_index=True, blank=True, default="")
    code = models.CharField(max_length=6)
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["email", "is_used"]),
            models.Index(fields=["phone", "is_used"]),
        ]

    def __str__(self):
        return f"OTP for {self.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_locked(self):
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
