"""
Customers serializers.
"""

from rest_framework import serializers
from customers.models import Customer, Installment, Subscription
from properties.serializers import PricingPlanSerializer


class CustomerSerializer(serializers.ModelSerializer):
    """Full customer representation."""

    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "email", "phone", "address",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "referral_source", "referral_code",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerCreateSerializer(serializers.ModelSerializer):
    """Create a customer — optionally with an initial subscription."""

    # Optional subscription fields
    property_id = serializers.UUIDField(required=False, write_only=True)
    pricing_plan_id = serializers.UUIDField(required=False, write_only=True)

    class Meta:
        model = Customer
        fields = [
            "full_name", "email", "phone", "address",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "referral_source", "referral_code",
            "property_id", "pricing_plan_id",
        ]


class InstallmentSerializer(serializers.ModelSerializer):
    """Installment representation."""

    class Meta:
        model = Installment
        fields = [
            "id", "subscription", "installment_number",
            "due_date", "amount", "status", "paid_date",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    """Full subscription representation with nested installments."""

    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)
    pricing_plan_name = serializers.CharField(source="pricing_plan.plan_name", read_only=True)
    installments = InstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "customer", "customer_name",
            "property", "property_name",
            "pricing_plan", "pricing_plan_name",
            "total_price", "amount_paid", "balance",
            "status", "start_date", "estimated_end_date",
            "notes", "installments",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_price", "amount_paid", "balance",
            "status", "estimated_end_date", "created_at", "updated_at",
        ]


class SubscriptionListSerializer(serializers.ModelSerializer):
    """Compact subscription representation for listings."""

    customer_name = serializers.CharField(source="customer.full_name", read_only=True)
    property_name = serializers.CharField(source="property.name", read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id", "customer", "customer_name",
            "property", "property_name",
            "total_price", "amount_paid", "balance",
            "status", "start_date", "estimated_end_date",
            "created_at",
        ]
        read_only_fields = fields


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Customer with subscriptions."""

    subscriptions = SubscriptionListSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "email", "phone", "address",
            "next_of_kin_name", "next_of_kin_phone", "next_of_kin_relationship",
            "referral_source", "referral_code",
            "subscriptions",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
