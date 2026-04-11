"""
Notifications serializers.
"""

from rest_framework import serializers
from notifications.models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            "id", "notification_type", "recipient",
            "subject", "message", "status",
            "sent_at", "error_message",
            "related_installment",
            "created_at",
        ]
        read_only_fields = fields
