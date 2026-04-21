"""
Customers serializers.
"""

from rest_framework import serializers
from customers.models import Customer, Installment, Subscription
from properties.serializers import PricingPlanSerializer


class CustomerListSerializer(serializers.ModelSerializer):
    """Customer list representation with primary subscription summary."""

    primary_subscription = serializers.SerializerMethodField()
    active_subscriptions = serializers.SerializerMethodField()
    completed_subscriptions = serializers.SerializerMethodField()
    defaulting_subscriptions = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "full_name", "email", "phone", "address",
            "referral_source", "referral_code",
            "primary_subscription",
            "active_subscriptions", "completed_subscriptions", "defaulting_subscriptions",
            "created_at",
        ]
        read_only_fields = fields

    def _subs(self, obj):
        if not hasattr(obj, "_subscription_cache"):
            obj._subscription_cache = list(obj.subscriptions.select_related(
                "property", "pricing_plan"
            ).order_by("-created_at"))
        return obj._subscription_cache

    def get_primary_subscription(self, obj):
        subs = self._subs(obj)
        sub = next((s for s in subs if s.status == "ACTIVE"), None) or (subs[0] if subs else None)
        if not sub:
            return None
        next_installment = (
            sub.installments.filter(status__in=["UPCOMING", "DUE", "OVERDUE"])
            .order_by("due_date").first()
        )
        return {
            "id": str(sub.id),
            "property_name": sub.property.name if sub.property else "",
            "land_size": getattr(sub.pricing_plan, "land_size", "") if sub.pricing_plan else "",
            "plan_name": sub.pricing_plan.plan_name if sub.pricing_plan else "",
            "payment_type": sub.pricing_plan.payment_type if sub.pricing_plan else "",
            "locked_price": str(sub.total_price),
            "amount_paid": str(sub.amount_paid),
            "balance": str(sub.balance),
            "status": sub.status,
            "next_due_date": str(next_installment.due_date) if next_installment else None,
            "next_due_amount": str(next_installment.amount) if next_installment else None,
        }

    def get_active_subscriptions(self, obj):
        return sum(1 for s in self._subs(obj) if s.status == "ACTIVE")

    def get_completed_subscriptions(self, obj):
        return sum(1 for s in self._subs(obj) if s.status == "COMPLETED")

    def get_defaulting_subscriptions(self, obj):
        return sum(1 for s in self._subs(obj) if s.status == "DEFAULTING")


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
