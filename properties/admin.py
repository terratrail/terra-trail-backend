from django.contrib import admin
from properties.models import (
    BankAccount,
    PricingPlan,
    Property,
    PropertyLocation,
    PropertyAmenity,
    PropertyDocument,
    PropertyGallery,
)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "workspace",
        "property_type",
        "status",
        "total_sqms",
        "created_at",
    ]
    list_filter = ["status", "property_type", "workspace"]
    search_fields = ["name"]


@admin.register(PropertyLocation)
class PropertyLocationAdmin(admin.ModelAdmin):
    list_display = ["property", "address", "city", "state", "country"]
    search_fields = ["address", "city"]


@admin.register(PricingPlan)
class PricingPlanAdmin(admin.ModelAdmin):
    list_display = [
        "plan_name",
        "property",
        "total_price",
        "payment_type",
        "monthly_installment",
        "is_active",
        "is_locked",
    ]
    list_filter = ["payment_type", "is_active", "is_locked"]
    search_fields = ["plan_name"]


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = [
        "bank_name",
        "account_name",
        "account_number",
        "property",
        "is_active",
    ]
    list_filter = ["is_active"]


@admin.register(PropertyAmenity)
class PropertyAmenityAdmin(admin.ModelAdmin):
    list_display = ["property", "name", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["property__name", "name"]


@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ["property", "document_type", "status", "created_at"]
    list_filter = ["document_type"]
    search_fields = ["property__name", "document_type"]


@admin.register(PropertyGallery)
class PropertyGalleryAdmin(admin.ModelAdmin):
    list_display = ["property", "image", "created_at"]
    list_filter = ["property"]
    search_fields = ["property__name"]
