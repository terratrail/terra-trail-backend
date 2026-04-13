"""
Core serializers — Workspace management.
"""

from rest_framework import serializers
from core.models import Workspace, WorkspaceSettings, WorkspaceActivity, WorkspaceInvitation


class WorkspaceSerializer(serializers.ModelSerializer):
    """Full workspace representation."""

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "logo", "timezone", "region",
            "initial_payment_as_first_month", "create_estate_public_pages",
            "intercom_app_id", "support_email", "support_whatsapp",
            "website_url", "instagram_url", "billing_plan", "plan_expires_at",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "billing_plan", "plan_expires_at", "created_at", "updated_at"]


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    """Granular workspace settings serializer."""

    class Meta:
        model = WorkspaceSettings
        fields = [
            "can_reps_approve_bookings", "can_reps_manage_subscriptions",
            "can_reps_manage_sales_reps", "notify_customer_on_booking_status",
            "notify_admin_on_new_booking", "notify_customer_on_payment_receipt",
        ]


class WorkspaceActivitySerializer(serializers.ModelSerializer):
    """Activity log serializer."""

    actor_name = serializers.CharField(source="actor.full_name", read_only=True)

    class Meta:
        model = WorkspaceActivity
        fields = ["id", "actor_name", "action_text", "category", "link", "created_at"]
        read_only_fields = ["id", "created_at"]


class WorkspaceInvitationSerializer(serializers.ModelSerializer):
    """Workspace invitation serializer."""

    invited_by_name = serializers.CharField(source="invited_by.full_name", read_only=True)

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id", "email", "role", "token", "invited_by_name",
            "expires_at", "is_accepted", "is_expired",
        ]
        read_only_fields = ["id", "token", "invited_by_name", "is_accepted"]


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for workspace creation."""

    class Meta:
        model = Workspace
        fields = ["name", "timezone", "region", "support_email", "support_whatsapp"]


class WorkspaceMinimalSerializer(serializers.ModelSerializer):
    """Minimal workspace representation for listings."""

    role = serializers.CharField(read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "logo", "role"]


class SelectPlanSerializer(serializers.Serializer):
    """
    Input for selecting/upgrading a billing plan.
    ENTERPRISE is excluded — it requires a direct sales conversation.
    """

    plan = serializers.ChoiceField(
        choices=["FREE", "STARTER", "GROWTH", "SCALE"],
        help_text="Choose a plan. For Enterprise, contact sales@terratrail.io.",
    )
