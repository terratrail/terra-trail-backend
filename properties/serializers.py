"""
Properties serializers.
"""

from decimal import Decimal
from django.db import transaction
from rest_framework import serializers
from properties.models import (
    BankAccount,
    InspectionConfig,
    LandSize,
    PricingPlan,
    Property,
    PropertyAmenity,
    PropertyAppreciation,
    PropertyDocument,
    PropertyGallery,
    PropertyLocation,
)


# ---------------------------------------------------------------------------
# Simple / standalone serializers
# ---------------------------------------------------------------------------


class PropertyLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyLocation
        fields = [
            "id",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "nearest_landmark",
            "latitude",
            "longitude",
        ]
        read_only_fields = ["id"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id",
            "property",
            "bank_name",
            "account_name",
            "account_number",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PricingPlanSerializer(serializers.ModelSerializer):
    monthly_installment = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = PricingPlan
        fields = [
            "id",
            "property",
            "plan_name",
            "land_size",
            "total_price",
            "payment_type",
            "initial_payment",
            "duration_months",
            "payment_spread_method",
            "monthly_installment",
            "is_active",
            "is_locked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "monthly_installment",
            "is_locked",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        """Prevent modifying spread method on locked plans."""
        if self.instance and self.instance.is_locked:
            if "payment_spread_method" in attrs:
                if (
                    attrs["payment_spread_method"]
                    != self.instance.payment_spread_method
                ):
                    raise serializers.ValidationError(
                        {
                            "payment_spread_method": "Cannot change spread method on a plan with active subscriptions."
                        }
                    )
        return attrs


class PricingPlanCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating pricing plans via the standalone endpoint."""

    class Meta:
        model = PricingPlan
        fields = [
            "property",
            "plan_name",
            "land_size",
            "total_price",
            "payment_type",
            "initial_payment",
            "duration_months",
            "payment_spread_method",
        ]


class PropertyAmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAmenity
        fields = [
            "id",
            "property",
            "name",
            "status",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(
        source="get_document_type_display", read_only=True
    )

    class Meta:
        model = PropertyDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "custom_document_name",
            "status",
            "document_file",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "document_type_display", "created_at", "updated_at"]


class PropertyGallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyGallery
        fields = ["id", "image", "caption", "order", "created_at"]
        read_only_fields = ["id", "created_at"]


class LandSizeSerializer(serializers.ModelSerializer):
    """Full land size representation (used in detail views)."""

    class Meta:
        model = LandSize
        fields = [
            "id",
            "property",
            "land_size",
            "total_slots",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Nested write serializers (used inside PropertyCreateSerializer)
# These omit the `property` FK — it is set automatically during creation.
# ---------------------------------------------------------------------------


class _AmenityNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAmenity
        fields = ["name", "status", "description"]


class _DocumentNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyDocument
        fields = ["document_type", "custom_document_name", "status", "notes"]


class _PricingPlanNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingPlan
        fields = [
            "plan_name",
            "land_size",
            "total_price",
            "payment_type",
            "initial_payment",
            "duration_months",
            "payment_spread_method",
        ]


class _BankAccountNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["bank_name", "account_name", "account_number"]


class _LandSizeNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandSize
        fields = ["land_size", "total_slots", "description"]


# ---------------------------------------------------------------------------
# List / detail serializers
# ---------------------------------------------------------------------------


class PropertyListSerializer(serializers.ModelSerializer):
    """Property listing with minimal related data."""

    location = PropertyLocationSerializer(read_only=True)
    pricing_plans_count = serializers.IntegerField(read_only=True)
    land_sizes = LandSizeSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "property_type",
            "description",
            "total_sqms",
            "available_units",
            "unit_measurement",
            "status",
            "featured_image",
            "location",
            "land_sizes",
            "pricing_plans_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Full property detail with all nested relations and commission info."""

    location = PropertyLocationSerializer(read_only=True)
    pricing_plans = PricingPlanSerializer(many=True, read_only=True)
    bank_accounts = BankAccountSerializer(many=True, read_only=True)
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    documents = PropertyDocumentSerializer(many=True, read_only=True)
    gallery_images = PropertyGallerySerializer(many=True, read_only=True)
    land_sizes = LandSizeSerializer(many=True, read_only=True)
    commission_defaults = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "property_type",
            "description",
            "total_sqms",
            "available_units",
            "unit_measurement",
            "status",
            "featured_image",
            "location",
            "gallery_images",
            "land_sizes",
            "pricing_plans",
            "bank_accounts",
            "amenities",
            "documents",
            # Commission overrides (null → use workspace default)
            "commission_override_starter",
            "commission_override_senior",
            "commission_override_legend",
            # Workspace defaults shown alongside for context
            "commission_defaults",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "commission_defaults",
            "created_at",
            "updated_at",
        ]

    def get_commission_defaults(self, obj):
        """Return workspace-level default commission rates."""
        from core.models import WorkspaceSettings

        try:
            ws = WorkspaceSettings.objects.get(workspace=obj.workspace)
            return {
                "starter": str(ws.commission_starter_pct),
                "senior": str(ws.commission_senior_pct),
                "legend": str(ws.commission_legend_pct),
            }
        except WorkspaceSettings.DoesNotExist:
            return {"starter": "0.00", "senior": "0.00", "legend": "0.00"}


# ---------------------------------------------------------------------------
# Public serializer (no sensitive data — bank accounts, commissions)
# ---------------------------------------------------------------------------


class PublicPropertySerializer(serializers.ModelSerializer):
    """Public-facing property serializer used by the unauthenticated estate listing."""

    location = PropertyLocationSerializer(read_only=True)
    pricing_plans = PricingPlanSerializer(many=True, read_only=True)
    gallery_images = PropertyGallerySerializer(many=True, read_only=True)
    amenities = PropertyAmenitySerializer(many=True, read_only=True)
    land_sizes = LandSizeSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            "id", "name", "property_type", "description",
            "total_sqms", "available_units", "unit_measurement",
            "status", "featured_image", "location",
            "gallery_images", "land_sizes", "pricing_plans", "amenities",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Create / update serializer  (all stepper fields in one request)
# ---------------------------------------------------------------------------


class PropertyCreateSerializer(serializers.ModelSerializer):
    """
    Create or update a property.

    Accepts all stepper fields in a single request:
      - Step 1: Basic information
      - Step 3: Location details  (nested `location`)
      - Step 4: Amenities         (nested list `amenities`)
      - Step 5: Property documents(nested list `documents`)
      - Step 6: Land inventory    (nested list `land_sizes`) — auto-computes total_sqms
      - Step 7: Pricing plans     (nested list `pricing_plans`)
      - Step 8: Bank accounts     (nested list `bank_accounts`)

    Gallery images (Step 2) are uploaded separately via
    POST /api/v1/properties/gallery/ because they are multipart uploads.
    """

    location = PropertyLocationSerializer(required=False)
    amenities = _AmenityNestedSerializer(many=True, required=False, default=list)
    documents = _DocumentNestedSerializer(many=True, required=False, default=list)
    pricing_plans = _PricingPlanNestedSerializer(
        many=True, required=False, default=list
    )
    bank_accounts = _BankAccountNestedSerializer(
        many=True, required=False, default=list
    )
    land_sizes = _LandSizeNestedSerializer(many=True, required=False, default=list)

    class Meta:
        model = Property
        fields = [
            "id",
            "name",
            "property_type",
            "description",
            "total_sqms",
            "available_units",
            "unit_measurement",
            "status",
            "featured_image",
            "location",
            "land_sizes",
            "amenities",
            "documents",
            "pricing_plans",
            "bank_accounts",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {
            "total_sqms": {"required": False, "allow_null": True},
            "available_units": {"required": False},
        }

    def _compute_from_land_sizes(self, land_sizes_data):
        """Return (total_sqms, available_units) computed from land_sizes list."""
        total_sqms = sum(
            Decimal(str(ls["land_size"])) * ls["total_slots"]
            for ls in land_sizes_data
        )
        available_units = sum(ls["total_slots"] for ls in land_sizes_data)
        return total_sqms, available_units

    @transaction.atomic
    def create(self, validated_data):
        location_data = validated_data.pop("location", None)
        amenities_data = validated_data.pop("amenities", [])
        documents_data = validated_data.pop("documents", [])
        pricing_plans_data = validated_data.pop("pricing_plans", [])
        bank_accounts_data = validated_data.pop("bank_accounts", [])
        land_sizes_data = validated_data.pop("land_sizes", [])

        # Auto-compute totals from land inventory
        if land_sizes_data:
            total_sqms, available_units = self._compute_from_land_sizes(land_sizes_data)
            validated_data["total_sqms"] = total_sqms
            validated_data["available_units"] = available_units

        workspace = validated_data.pop("workspace", None) or self.context["request"].workspace
        property_obj = Property.objects.create(workspace=workspace, **validated_data)

        if location_data:
            PropertyLocation.objects.create(
                workspace=workspace, property=property_obj, **location_data
            )

        for item in land_sizes_data:
            LandSize.objects.create(
                workspace=workspace, property=property_obj, **item
            )

        for item in amenities_data:
            PropertyAmenity.objects.create(
                workspace=workspace, property=property_obj, **item
            )

        for item in documents_data:
            PropertyDocument.objects.create(
                workspace=workspace, property=property_obj, **item
            )

        for item in pricing_plans_data:
            PricingPlan.objects.create(
                workspace=workspace, property=property_obj, **item
            )

        for item in bank_accounts_data:
            BankAccount.objects.create(
                workspace=workspace, property=property_obj, **item
            )

        return property_obj

    def update(self, instance, validated_data):
        location_data = validated_data.pop("location", None)
        amenities_data = validated_data.pop("amenities", None)
        documents_data = validated_data.pop("documents", None)
        pricing_plans_data = validated_data.pop("pricing_plans", None)
        bank_accounts_data = validated_data.pop("bank_accounts", None)
        land_sizes_data = validated_data.pop("land_sizes", None)

        # Auto-compute totals when land_sizes are provided
        if land_sizes_data is not None:
            total_sqms, available_units = self._compute_from_land_sizes(land_sizes_data)
            validated_data["total_sqms"] = total_sqms
            validated_data["available_units"] = available_units

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        workspace = instance.workspace

        if location_data is not None:
            PropertyLocation.objects.update_or_create(
                property=instance,
                defaults={**location_data, "workspace": workspace},
            )

        if land_sizes_data is not None:
            instance.land_sizes.all().delete()
            for item in land_sizes_data:
                LandSize.objects.create(
                    workspace=workspace, property=instance, **item
                )

        if amenities_data is not None:
            instance.amenities.all().delete()
            for item in amenities_data:
                PropertyAmenity.objects.create(
                    workspace=workspace, property=instance, **item
                )

        if documents_data is not None:
            instance.documents.all().delete()
            for item in documents_data:
                PropertyDocument.objects.create(
                    workspace=workspace, property=instance, **item
                )

        if pricing_plans_data is not None:
            instance.pricing_plans.filter(is_locked=False).delete()
            for item in pricing_plans_data:
                PricingPlan.objects.create(
                    workspace=workspace, property=instance, **item
                )

        if bank_accounts_data is not None:
            instance.bank_accounts.all().delete()
            for item in bank_accounts_data:
                BankAccount.objects.create(
                    workspace=workspace, property=instance, **item
                )

        return instance


# ---------------------------------------------------------------------------
# InspectionConfig serializer
# ---------------------------------------------------------------------------

class InspectionConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionConfig
        fields = [
            "id", "property", "meeting_point", "virtual_link",
            "available_days", "time_from", "time_to", "max_persons", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# PropertyAppreciation serializer
# ---------------------------------------------------------------------------

class PropertyAppreciationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyAppreciation
        fields = [
            "id", "property", "effective_date", "old_price", "new_price",
            "percentage_change", "notes", "created_at",
        ]
        read_only_fields = ["id", "percentage_change", "created_at"]
