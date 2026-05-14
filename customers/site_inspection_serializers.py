"""
SiteInspection serializers.
"""

from rest_framework import serializers
from customers.site_inspection_models import SiteInspection


class SiteInspectionSerializer(serializers.ModelSerializer):
    property_display = serializers.SerializerMethodField()
    attended = serializers.BooleanField(read_only=True)
    assigned_rep_name = serializers.SerializerMethodField()
    converted_customer_name = serializers.SerializerMethodField()
    is_converted = serializers.SerializerMethodField()

    class Meta:
        model = SiteInspection
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "linked_property",
            "property_name",
            "property_display",
            "inspection_date",
            "inspection_time",
            "inspection_type",
            "category",
            "persons",
            "attendees",
            "status",
            "attended",
            "notes",
            "assigned_rep",
            "assigned_rep_name",
            "converted_customer",
            "converted_customer_name",
            "is_converted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "attended", "is_converted", "created_at", "updated_at"]

    def get_property_display(self, obj):
        if obj.linked_property:
            return obj.linked_property.name
        return obj.property_name

    def get_assigned_rep_name(self, obj):
        if not obj.assigned_rep:
            return None
        return obj.assigned_rep.get_full_name() or obj.assigned_rep.email

    def get_converted_customer_name(self, obj):
        if not obj.converted_customer:
            return None
        return obj.converted_customer.full_name

    def get_is_converted(self, obj):
        return obj.converted_customer_id is not None


class SiteInspectionCreateSerializer(serializers.ModelSerializer):
    attendees = serializers.JSONField(required=False, default=list)

    class Meta:
        model = SiteInspection
        fields = [
            "name",
            "email",
            "phone",
            "linked_property",
            "property_name",
            "inspection_date",
            "inspection_time",
            "inspection_type",
            "category",
            "persons",
            "attendees",
            "notes",
        ]
