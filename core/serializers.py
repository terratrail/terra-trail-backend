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
            "website_url", "instagram_url", "facebook_url", "twitter_url",
            "linkedin_url", "youtube_url",
            "billing_plan", "plan_expires_at",
            "billing_pending_plan", "billing_pending_at",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "billing_plan", "plan_expires_at",
            "billing_pending_plan", "billing_pending_at",
            "created_at", "updated_at",
        ]


class WorkspaceSettingsSerializer(serializers.ModelSerializer):
    """Granular workspace settings serializer."""

    class Meta:
        model = WorkspaceSettings
        fields = [
            # Permissions
            "can_reps_approve_bookings", "can_reps_manage_subscriptions",
            "can_reps_manage_sales_reps",
            # Notification toggles
            "notify_customer_on_booking_status", "notify_booking_rejected",
            "notify_admin_on_new_booking",
            "notify_customer_on_payment_receipt", "notify_payment_approved",
            "notify_payment_rejected", "notify_payment_reminder_7d",
            "notify_payment_reminder_2d", "notify_payment_due_today",
            "notify_payment_overdue", "notify_subscription_completed",
            "notify_property_published",
            "notify_realtor_added", "notify_commission_paid",
            "notify_plot_allocated",
            # Commission defaults
            "commission_starter_pct", "commission_senior_pct", "commission_legend_pct",
        ]


class WorkspaceActivitySerializer(serializers.ModelSerializer):
    """Activity log serializer."""

    actor_name = serializers.SerializerMethodField()

    def get_actor_name(self, obj):
        if obj.actor:
            name = obj.actor.full_name or ""
            if not name.strip():
                name = obj.actor.email or "Unknown"
            return name
        return "Terratrail System"

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
        read_only_fields = ["id", "token", "invited_by_name", "expires_at", "is_accepted", "is_expired"]


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for workspace creation."""

    slug = serializers.SlugField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Custom workspace URL slug. Auto-generated from name if omitted.",
    )

    def validate_slug(self, value):
        if value and Workspace.objects.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already taken.")
        return value

    class Meta:
        model = Workspace
        fields = ["name", "slug", "timezone", "region", "support_email", "support_whatsapp"]


class WorkspaceMinimalSerializer(serializers.ModelSerializer):
    """Minimal workspace representation for listings."""

    role = serializers.CharField(read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "logo", "billing_plan", "role"]


class SelectPlanSerializer(serializers.Serializer):
    """
    Input for selecting/upgrading a billing plan.
    ENTERPRISE is excluded — it requires a direct sales conversation.
    """

    plan = serializers.ChoiceField(
        choices=["FREE", "STARTER", "GROWTH", "SCALE"],
        help_text="Choose a plan. For Enterprise, contact sales@terratrail.io.",
    )
