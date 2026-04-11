"""
Accounts services — Authentication and OTP business logic.

All auth-related business logic lives here, not in views or signals.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import OTPToken, User, WorkspaceMembership
from core.models import Workspace
from core.utils import generate_otp


class AuthService:
    """Handles user registration and JWT login."""

    @staticmethod
    def register_user(email, password, first_name="", last_name="", phone=""):
        """
        Register a new user.

        Returns:
            tuple: (user, tokens_dict)
        """
        if User.objects.filter(email=email).exists():
            raise ValueError("A user with this email already exists.")

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

        tokens = AuthService._generate_tokens(user)
        return user, tokens

    @staticmethod
    def login_user(email, password):
        """
        Authenticate and return JWT tokens.

        Returns:
            tuple: (user, tokens_dict)

        Raises:
            ValueError: If credentials are invalid.
        """
        user = authenticate(email=email, password=password)
        if not user:
            raise ValueError("Invalid email or password.")
        if not user.is_active:
            raise ValueError("Account is deactivated.")

        tokens = AuthService._generate_tokens(user)
        return user, tokens

    @staticmethod
    def _generate_tokens(user):
        """Generate JWT access and refresh tokens for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class OTPService:
    """Handles OTP generation, validation, and lockout for customer portal."""

    @staticmethod
    def request_otp(email, phone):
        """
        Generate and store a new OTP.

        Validates that email + phone match a known customer before issuing.
        Returns the OTP code (for sending via email/SMS).
        """
        # Check for existing lockout
        recent_otp = (
            OTPToken.objects.filter(email=email, is_used=False)
            .order_by("-created_at")
            .first()
        )
        if recent_otp and recent_otp.is_locked:
            remaining = (recent_otp.locked_until - timezone.now()).seconds // 60
            raise ValueError(
                f"Account locked. Try again in {remaining + 1} minutes."
            )

        # Generate new OTP
        code = generate_otp()
        expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        otp = OTPToken.objects.create(
            email=email,
            phone=phone,
            code=code,
            expires_at=expiry,
        )

        return otp.code

    @staticmethod
    def verify_otp(email, code):
        """
        Verify an OTP code.

        Returns:
            User if valid, raises ValueError otherwise.
        """
        otp = (
            OTPToken.objects.filter(email=email, is_used=False)
            .order_by("-created_at")
            .first()
        )

        if not otp:
            raise ValueError("No pending OTP found. Request a new one.")

        if otp.is_locked:
            raise ValueError("Account locked due to too many attempts.")

        if otp.is_expired:
            raise ValueError("OTP has expired. Request a new one.")

        if otp.code != code:
            otp.attempts += 1
            if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp.locked_until = timezone.now() + timedelta(
                    minutes=settings.OTP_LOCKOUT_MINUTES
                )
            otp.save()
            remaining = settings.OTP_MAX_ATTEMPTS - otp.attempts
            raise ValueError(
                f"Invalid OTP. {remaining} attempt(s) remaining."
            )

        # Mark OTP as used
        otp.is_used = True
        otp.save()

        # Return or create session token
        try:
            user = User.objects.get(email=email)
            tokens = AuthService._generate_tokens(user)
            return user, tokens
        except User.DoesNotExist:
            raise ValueError("No user account found for this email.")


class WorkspaceService:
    """Handles workspace-related business logic."""

    @staticmethod
    def create_workspace(user, name, **kwargs):
        """Create a workspace and assign user as OWNER."""
        workspace = Workspace.objects.create(name=name, **kwargs)
        WorkspaceMembership.objects.create(
            user=user,
            workspace=workspace,
            role=WorkspaceMembership.Role.OWNER,
            is_active=True,
        )
        return workspace

    @staticmethod
    def add_member(workspace, user, role="ADMIN"):
        """Add a user to a workspace with a specified role."""
        membership, created = WorkspaceMembership.objects.get_or_create(
            user=user,
            workspace=workspace,
            defaults={"role": role, "is_active": True},
        )
        if not created:
            membership.role = role
            membership.is_active = True
            membership.save()
        return membership

    @staticmethod
    def get_user_workspaces(user):
        """Get all active workspaces for a user."""
        return Workspace.objects.filter(
            memberships__user=user,
            memberships__is_active=True,
            is_active=True,
        )
