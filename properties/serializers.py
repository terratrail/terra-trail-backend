"""
Properties serializers.
"""

from rest_framework import serializers
from properties.models import BankAccount, PricingPlan, Property, PropertyLocation


class PropertyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyLocation
        fields = [
            "id", "address", "city", "state", "country",
            "postal_code", "latitude", "longitude",
        ]
        read_only_fields = ["id"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id", "bank_name", "account_name", "account_number",
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PricingPlanSerializer(serializers.ModelSerializer):
    monthly_installment = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = PricingPlan
        fields = [
            "id", "property", "plan_name", "land_size", "total_price",
            "payment_type", "initial_payment", "duration_months",
            "payment_spread_method", "monthly_installment",
            "is_active", "is_locked", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "monthly_installment", "is_locked", "created_at", "updated_at"]

    def validate(self, attrs):
        """Prevent modifying spread method on locked plans."""
        if self.instance and self.instance.is_locked:
            if "payment_spread_method" in attrs:
                if attrs["payment_spread_method"] != self.instance.payment_spread_method:
                    raise serializers.ValidationError(
                        {"payment_spread_method": "Cannot change spread method on a plan with active subscriptions."}
                    )
        return attrs


class PricingPlanCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating pricing plans."""

    class Meta:
        model = PricingPlan
        fields = [
            "property", "plan_name", "land_size", "total_price",
            "payment_type", "initial_payment", "duration_months",
            "payment_spread_method",
        ]


class PropertyListSerializer(serializers.ModelSerializer):
    """Property listing with minimal related data."""

    location = PropertyLocationSerializer(read_only=True)
    pricing_plans_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Property
        fields = [
            "id", "name", "property_type", "description",
            "total_sqms", "unit_measurement", "status",
            "featured_image", "location", "pricing_plans_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Full property detail with nested relations."""

    location = PropertyLocationSerializer(read_only=True)
    pricing_plans = PricingPlanSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id", "name", "property_type", "description",
            "total_sqms", "unit_measurement", "status",
            "featured_image", "location", "pricing_plans",
            "bank_accounts", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyCreateSerializer(serializers.ModelSerializer):
    """Create/update a property with optional location."""

    location = PropertyLocationSerializer(required=False)

    class Meta:
        model = Property
        fields = [
            "name", "property_type", "description",
            "total_sqms", "unit_measurement", "featured_image",
            "location",
        ]

    def create(self, validated_data):
        location_data = validated_data.pop("location", None)
        workspace = self.context["request"].workspace
        property_obj = Property.objects.create(workspace=workspace, **validated_data)

        if location_data:
            PropertyLocation.objects.create(
                workspace=workspace,
                property=property_obj,
                **location_data,
            )

        return property_obj

    def update(self, instance, validated_data):
        location_data = validated_data.pop("location", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if location_data:
            PropertyLocation.objects.update_or_create(
                property=instance,
                defaults={**location_data, "workspace": instance.workspace},
            )

        return instance
