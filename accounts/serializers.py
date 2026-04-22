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
            "title", "gender", "birth_month", "birth_day", "occupation",
            "marital_status", "address", "country", "state",
            "nationality", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    """User registration input."""

    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone = serializers.CharField(max_length=20, required=False, default="")
    title = serializers.CharField(max_length=10, required=False, default="")
    gender = serializers.CharField(max_length=10, required=False, default="")
    birth_month = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=12)
    birth_day = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    occupation = serializers.CharField(max_length=255, required=False, default="")
    marital_status = serializers.CharField(max_length=20, required=False, default="")
    address = serializers.CharField(required=False, default="")
    country = serializers.CharField(max_length=100, required=False, default="Nigeria")
    state = serializers.CharField(max_length=100, required=False, default="")
    nationality = serializers.CharField(max_length=100, required=False, default="")


class LoginSerializer(serializers.Serializer):
    """User login input."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class OTPRequestSerializer(serializers.Serializer):
    """OTP request input — customer portal."""

    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise serializers.ValidationError("Either email or phone is required.")
        return data


class OTPVerifySerializer(serializers.Serializer):
    """OTP verification input."""

    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, data):
        if not data.get("email") and not data.get("phone"):
            raise serializers.ValidationError("Either email or phone is required for verification.")
        return data


class WorkspaceMembershipSerializer(serializers.ModelSerializer):
    """Workspace membership representation."""

    user_email = serializers.CharField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = WorkspaceMembership
        fields = [
            "id", "user", "user_email", "user_name", "user_phone",
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
