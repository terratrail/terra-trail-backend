"""
Core serializers — Workspace management.
"""

from rest_framework import serializers
from core.models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    """Full workspace representation."""

    class Meta:
        model = Workspace
        fields = [
            "id", "name", "slug", "logo", "timezone",
            "support_email", "support_whatsapp", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    """Serializer for workspace creation."""

    class Meta:
        model = Workspace
        fields = ["name", "timezone", "support_email", "support_whatsapp"]

    def create(self, validated_data):
        workspace = Workspace.objects.create(**validated_data)
        return workspace


class WorkspaceMinimalSerializer(serializers.ModelSerializer):
    """Minimal workspace representation for listings."""

    role = serializers.CharField(read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "logo", "role"]
