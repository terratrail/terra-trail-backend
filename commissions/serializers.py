"""
Commissions serializers.
"""

from rest_framework import serializers
from commissions.models import Commission, SalesRep


class SalesRepSerializer(serializers.ModelSerializer):
    """Full sales rep representation."""

    total_earned = serializers.SerializerMethodField()
    total_pending = serializers.SerializerMethodField()

    class Meta:
        model = SalesRep
        fields = [
            "id", "name", "email", "phone", "tier",
            "referral_code", "commission_type", "commission_rate",
            "is_active", "total_earned", "total_pending",
            "address", "bank_name", "bank_account_number", "bank_account_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_earned(self, obj):
        return str(
            sum(c.amount for c in obj.commissions.all())
        )

    def get_total_pending(self, obj):
        return str(
            sum(c.amount for c in obj.commissions.filter(status="PENDING"))
        )


class SalesRepCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesRep
        fields = [
            "name", "email", "phone", "tier",
            "referral_code", "commission_type", "commission_rate",
            "address", "bank_name", "bank_account_number", "bank_account_name",
        ]


class CommissionSerializer(serializers.ModelSerializer):
    """Commission representation."""

    sales_rep_name = serializers.CharField(source="sales_rep.name", read_only=True)
    transaction_reference = serializers.CharField(
        source="payment.transaction_reference", read_only=True
    )

    class Meta:
        model = Commission
        fields = [
            "id", "sales_rep", "sales_rep_name",
            "payment", "transaction_reference",
            "amount", "status", "paid_date", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "sales_rep", "payment", "amount",
            "created_at", "updated_at",
        ]
