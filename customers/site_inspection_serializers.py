"""
SiteInspection serializers.
"""

from rest_framework import serializers
from customers.site_inspection_models import SiteInspection


class SiteInspectionSerializer(serializers.ModelSerializer):
    property_display = serializers.SerializerMethodField()
    attended = serializers.BooleanField(read_only=True)

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
            "status",
            "attended",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "attended", "created_at", "updated_at"]

    def get_property_display(self, obj):
        if obj.linked_property:
            return obj.linked_property.name
        return obj.property_name


class SiteInspectionCreateSerializer(serializers.ModelSerializer):
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
            "notes",
        ]
