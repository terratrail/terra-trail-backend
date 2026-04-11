"""
Accounts serializers — Auth, User, Membership.
"""

from rest_framework import serializers
from accounts.models import User, WorkspaceMembership


class UserSerializer(serializers.ModelSerializer):
    """Full user representation."""

    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "email", "phone", "first_name", "last_name",
            "full_name", "default_role", "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    """User registration input."""

    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone = serializers.CharField(max_length=20, required=False, default="")


class LoginSerializer(serializers.Serializer):
    """User login input."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPRequestSerializer(serializers.Serializer):
    """OTP request input — customer portal."""

    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)


class OTPVerifySerializer(serializers.Serializer):
    """OTP verification input."""

    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    """Workspace membership representation."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = [
            "id", "user", "user_email", "user_name",
            "workspace", "workspace_name", "role", "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AddMemberSerializer(serializers.Serializer):
    """Add a member to the workspace."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=WorkspaceMembership.Role.choices,
        default="ADMIN",
    )
