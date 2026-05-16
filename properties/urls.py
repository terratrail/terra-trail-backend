"""
Properties URL configuration.
"""

from django.urls import path
from properties.views import (
    AssignCustomerRepView,
    BankAccountDetailView,
    BankAccountListCreateView,
    InspectionConfigView,
    InspectionConfigListCreateView,
    InspectionConfigDetailView,
    PricingPlanActivateView,
    PricingPlanDeactivateView,
    PricingPlanDetailView,
    PricingPlanHistoryView,
    PricingPlanListCreateView,
    PropertyAmenityDetailView,
    PropertyAmenityListCreateView,
    PropertyAppreciationDetailView,
    PropertyAppreciationListCreateView,
    PropertyAvailableSlotsView,
    PropertyDetailView,
    PropertyDocumentDetailView,
    PropertyDocumentListCreateView,
    PropertyGalleryDetailView,
    PropertyGalleryListCreateView,
    PropertyListCreateView,
    PropertyPublishView,
    PropertyUnpublishView,
)
from properties.bulk_upload_views import PropertyBulkUploadView, PropertyBulkTemplateView

app_name = "properties"

urlpatterns = [
    # Properties
    path("", PropertyListCreateView.as_view(), name="property-list-create"),
    path("<uuid:id>/", PropertyDetailView.as_view(), name="property-detail"),
    path("<uuid:id>/publish/",   PropertyPublishView.as_view(),   name="property-publish"),
    path("<uuid:id>/unpublish/", PropertyUnpublishView.as_view(), name="property-unpublish"),
    path("<uuid:id>/assign-customer-rep/", AssignCustomerRepView.as_view(), name="property-assign-rep"),

    # Pricing Plans  (?property_id=<uuid> to filter)
    path("plans/", PricingPlanListCreateView.as_view(), name="plan-list-create"),
    path("plans/<uuid:id>/", PricingPlanDetailView.as_view(), name="plan-detail"),
    path("plans/<uuid:id>/activate/",   PricingPlanActivateView.as_view(),   name="plan-activate"),
    path("plans/<uuid:id>/deactivate/", PricingPlanDeactivateView.as_view(), name="plan-deactivate"),
    path("plans/<uuid:id>/history/",    PricingPlanHistoryView.as_view(),    name="plan-history"),

    # Bank Accounts  (?property_id=<uuid> to filter)
    path("bank-accounts/", BankAccountListCreateView.as_view(), name="bank-list-create"),
    path("bank-accounts/<uuid:id>/", BankAccountDetailView.as_view(), name="bank-detail"),

    # Amenities  (?property_id=<uuid> to filter)
    path("amenities/", PropertyAmenityListCreateView.as_view(), name="amenity-list-create"),
    path("amenities/<uuid:id>/", PropertyAmenityDetailView.as_view(), name="amenity-detail"),

    # Documents  (?property_id=<uuid> to filter)
    path("documents/", PropertyDocumentListCreateView.as_view(), name="document-list-create"),
    path("documents/<uuid:id>/", PropertyDocumentDetailView.as_view(), name="document-detail"),

    # Gallery images  (?property_id=<uuid> to filter)
    path("gallery/", PropertyGalleryListCreateView.as_view(), name="gallery-list-create"),
    path("gallery/<uuid:id>/", PropertyGalleryDetailView.as_view(), name="gallery-detail"),

    # Bulk upload
    path("bulk-upload/", PropertyBulkUploadView.as_view(), name="property-bulk-upload"),
    path("bulk-upload/template/", PropertyBulkTemplateView.as_view(), name="property-bulk-template"),

    # Inspection Config — legacy single-config endpoint
    path("<uuid:id>/inspection-config/", InspectionConfigView.as_view(), name="inspection-config"),

    # Inspection Configs — multi-config endpoints
    path("<uuid:id>/inspection-configs/", InspectionConfigListCreateView.as_view(), name="inspection-configs-list-create"),
    path("<uuid:id>/inspection-configs/<uuid:config_id>/", InspectionConfigDetailView.as_view(), name="inspection-config-detail"),

    # Available slots
    path("<uuid:id>/available-slots/", PropertyAvailableSlotsView.as_view(), name="available-slots"),

    # Appreciation records
    path("<uuid:id>/appreciations/", PropertyAppreciationListCreateView.as_view(), name="appreciation-list-create"),
    path("<uuid:id>/appreciations/<uuid:appr_id>/", PropertyAppreciationDetailView.as_view(), name="appreciation-detail"),
]
