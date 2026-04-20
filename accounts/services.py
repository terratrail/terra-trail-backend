"""
Accounts services — Authentication and OTP business logic.

All auth-related business logic lives here, not in views or signals.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import OTPToken, User, WorkspaceMembership
from core.models import Workspace
from core.utils import generate_otp


class AuthService:
    """Handles user registration and JWT login."""

    @staticmethod
    def register_user(email, password, **extra_fields):
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
            is_active=False,  # Require OTP verification
            **extra_fields,
        )

        # Trigger OTP — send_otp_email is called inside OTPService.request_otp
        OTPService.request_otp(email=user.email, phone=user.phone)

        return user, None  # No tokens until verified

    @staticmethod
    def login_user(email, password):
        """
        Authenticate and return JWT tokens.
        """
        user = authenticate(email=email, password=password)

        if not user:
            # Check if user exists but is inactive
            try:
                temp_user = User.objects.get(email=email)
                if not temp_user.is_active:
                    raise ValueError(
                        "Your account is not verified. Please verify your email via OTP."
                    )
                if not temp_user.check_password(password):
                    raise ValueError("Invalid email or password.")
            except User.DoesNotExist:
                raise ValueError("Invalid email or password.")

            raise ValueError("Invalid email or password.")

        tokens = AuthService._generate_tokens(user)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

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
    def request_otp(email="", phone=""):
        """
        Generate and store a new OTP.

        Validates that email OR phone is provided.
        Returns the OTP code (for sending via email/SMS).
        """
        if not email and not phone:
            raise ValueError("Email or phone is required.")

        # Check for existing lockout across both identifiers if both provided
        from django.db.models import Q

        recent_otp = (
            OTPToken.objects.filter(
                Q(email=email, email__gt="") | Q(phone=phone, phone__gt=""),
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )

        if recent_otp and recent_otp.is_locked:
            remaining = (recent_otp.locked_until - timezone.now()).seconds // 60
            raise ValueError(f"Account locked. Try again in {remaining + 1} minutes.")

        # Generate new OTP
        code = generate_otp()
        expiry = timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)

        otp = OTPToken.objects.create(
            email=email,
            phone=phone,
            code=code,
            expires_at=expiry,
        )

        # Trigger notification based on available contact method
        from notifications.services import NotificationService

        if email:
            NotificationService.send_otp_email(
                recipient=email,
                code=code,
            )
        elif phone:
            NotificationService.send_sms(
                workspace=None,
                recipient=phone,
                message=f"Your TerraTrail OTP is {code}. Expires in 10m.",
            )

        return otp.code

    @staticmethod
    def verify_otp(code, email="", phone=""):
        """
        Verify an OTP code.

        Returns:
            User if valid, raises ValueError otherwise.
        """
        from django.db.models import Q

        if not email and not phone:
            raise ValueError("Email or phone is required for verification.")

        # Filter by whichever identifier is provided
        lookup = Q(is_used=False)
        if email:
            lookup &= Q(email=email)
        elif phone:
            lookup &= Q(phone=phone)

        otp = OTPToken.objects.filter(lookup).order_by("-created_at").first()

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
            raise ValueError(f"Invalid OTP. {remaining} attempt(s) remaining.")

        # Mark OTP as used
        otp.is_used = True
        otp.save()

        # Activate user if they were inactive
        try:
            lookup = Q()
            if email:
                lookup = Q(email=email)
            elif phone:
                lookup = Q(phone=phone)

            user = User.objects.get(lookup)
            if not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active", "updated_at"])

            tokens = AuthService._generate_tokens(user)
            return user, tokens
        except User.DoesNotExist:
            raise ValueError("No user account found for this email.")


    @staticmethod
    def verify_otp_for_portal(code, email="", phone=""):
        """
        Verify an OTP for the customer self-service portal.

        Unlike verify_otp(), this does NOT look up a User record — it only
        validates the OTP token. The caller is responsible for fetching the
        Customer and creating a portal session.

        Raises ValueError on failure (invalid, expired, locked).
        """
        from django.db.models import Q

        if not email and not phone:
            raise ValueError("Email or phone is required for verification.")

        lookup = Q(is_used=False)
        if email:
            lookup &= Q(email=email)
        if phone:
            lookup &= Q(phone=phone)

        otp = OTPToken.objects.filter(lookup).order_by("-created_at").first()

        if not otp:
            raise ValueError("No pending OTP found. Please request a new one.")

        if otp.is_locked:
            raise ValueError("Account locked due to too many failed attempts. Try again later.")

        if otp.is_expired:
            raise ValueError("OTP has expired. Please request a new one.")

        if otp.code != code:
            otp.attempts += 1
            if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
                otp.locked_until = timezone.now() + timedelta(
                    minutes=settings.OTP_LOCKOUT_MINUTES
                )
            otp.save()
            remaining = max(settings.OTP_MAX_ATTEMPTS - otp.attempts, 0)
            raise ValueError(f"Invalid OTP. {remaining} attempt(s) remaining.")

        otp.is_used = True
        otp.save(update_fields=["is_used"])


class WorkspaceService:
    """Handles workspace-related business logic."""

    @staticmethod
    @transaction.atomic
    def create_workspace(user, name, **kwargs):
        """
        Create a workspace, assign user as OWNER,
        initialize settings, and log activity.

        A welcome email is dispatched after the transaction commits so that
        a failing SMTP call never rolls back a valid workspace creation.
        """
        workspace = Workspace.objects.create(name=name, **kwargs)

        # Assign Owner
        WorkspaceMembership.objects.create(
            user=user,
            workspace=workspace,
            role=WorkspaceMembership.Role.OWNER,
            is_active=True,
        )

        # Initialize Default Settings
        from core.models import WorkspaceSettings, WorkspaceActivity

        WorkspaceSettings.objects.create(workspace=workspace)

        # Log Activity
        WorkspaceActivity.objects.create(
            workspace=workspace,
            actor=user,
            action_text=f"created workspace '{name}'",
            category="Workspace",
        )

        # Send welcome email after the transaction commits successfully
        workspace_id = workspace.id
        user_email = user.email
        user_name = user.full_name

        def _send_welcome():
            from core.models import Workspace as _Workspace
            from notifications.services import NotificationService
            from terratrail.config import settings as app_settings

            try:
                _workspace = _Workspace.objects.get(pk=workspace_id)
            except _Workspace.DoesNotExist:
                return

            NotificationService.send_welcome_email(
                recipient=user_email,
                user_name=user_name,
                workspace_name=name,
                workspace_region=getattr(_workspace, "region", ""),
                support_email=app_settings.SUPPORT_EMAIL,
            )

        transaction.on_commit(_send_welcome)

        return workspace

    @staticmethod
    def add_member(workspace, user, role="ADMIN"):
        """Add a user to a workspace with a specified role."""
        # Only check the limit when adding a genuinely new active member.
        # Re-activating or updating an existing membership doesn't consume a slot.
        already_member = WorkspaceMembership.objects.filter(
            user=user, workspace=workspace, is_active=True
        ).exists()
        if not already_member:
            from core.plan_guard import PlanGuard, PlanLimitExceeded

            PlanGuard.check_team_member_limit(workspace)

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
