"""
Payments serializers.
"""

from decimal import Decimal

from rest_framework import serializers
from payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Full payment representation."""

    recorded_by_email = serializers.CharField(
        source="recorded_by.email", read_only=True, default=None
    )
    approved_by_email = serializers.CharField(
        source="approved_by.email", read_only=True, default=None
    )
    recorded_by_name = serializers.SerializerMethodField()
    customer_name = serializers.CharField(
        source="installment.subscription.customer.full_name",
        read_only=True,
    )
    land_size = serializers.CharField(
        source="installment.subscription.pricing_plan.land_size",
        read_only=True, default=None,
    )
    property_id = serializers.UUIDField(
        source="installment.subscription.property.id",
        read_only=True, default=None,
    )
    property_name = serializers.CharField(
        source="installment.subscription.property.name",
        read_only=True, default=None,
    )
    installment_number = serializers.IntegerField(
        source="installment.installment_number", read_only=True,
    )

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return f"{obj.recorded_by.first_name} {obj.recorded_by.last_name}".strip() or obj.recorded_by.email
        return None

    class Meta:
        model = Payment
        fields = [
            "id", "installment", "installment_number",
            "customer_name", "land_size", "property_id", "property_name",
            "amount", "payment_date",
            "status", "recorded_by", "recorded_by_email", "recorded_by_name",
            "approved_by", "approved_by_email",
            "receipt_url", "receipt_file",
            "transaction_reference", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "payment_date", "status", "approved_by",
            "transaction_reference", "created_at", "updated_at",
        ]


class RecordPaymentSerializer(serializers.Serializer):
    """Input for recording a payment."""

    installment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    receipt_url = serializers.URLField(required=False, default="")
    receipt_file = serializers.FileField(required=False, default=None)
    notes = serializers.CharField(required=False, default="")


class ApproveRejectSerializer(serializers.Serializer):
    """Input for approving/rejecting a payment."""

    reason = serializers.CharField(required=False, default="")
