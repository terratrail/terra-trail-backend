"""
Customers URL configuration.
"""

from django.urls import path
from customers.views import (
    AllocateSubscriptionView,
    CancelSubscriptionView,
    CustomerDetailView,
    CustomerListCreateView,
    InstallmentListView,
    SubscriptionCreateView,
    SubscriptionDetailView,
    SubscriptionListView,
)
from customers.site_inspection_views import (
    SiteInspectionListCreateView,
    SiteInspectionDetailView,
)
from customers.bulk_upload_views import CustomerBulkUploadView, CustomerBulkTemplateView
from customers.bulk_upload_extra_views import (
    SiteInspectionBulkUploadView,
    SiteInspectionBulkTemplateView,
    SubscriptionBulkUploadView,
    SubscriptionBulkTemplateView,
    InstallmentBulkUploadView,
    InstallmentBulkTemplateView,
)

app_name = "customers"

urlpatterns = [
    # Customers
    path("", CustomerListCreateView.as_view(), name="customer-list-create"),
    path("<uuid:id>/", CustomerDetailView.as_view(), name="customer-detail"),

    # Subscriptions
    path("subscriptions/", SubscriptionListView.as_view(), name="subscription-list"),
    path("subscriptions/create/", SubscriptionCreateView.as_view(), name="subscription-create"),
    path("subscriptions/<uuid:id>/", SubscriptionDetailView.as_view(), name="subscription-detail"),
    path("subscriptions/<uuid:id>/allocate/", AllocateSubscriptionView.as_view(), name="subscription-allocate"),
    path("subscriptions/<uuid:id>/cancel/", CancelSubscriptionView.as_view(), name="subscription-cancel"),

    # Installments
    path("installments/", InstallmentListView.as_view(), name="installment-list"),

    # Site Inspections
    path("site-inspections/", SiteInspectionListCreateView.as_view(), name="site-inspection-list"),
    path("site-inspections/<uuid:id>/", SiteInspectionDetailView.as_view(), name="site-inspection-detail"),

    # Bulk upload — Customers
    path("bulk-upload/", CustomerBulkUploadView.as_view(), name="customer-bulk-upload"),
    path("bulk-upload/template/", CustomerBulkTemplateView.as_view(), name="customer-bulk-template"),

    # Bulk upload — Site Inspections
    path("inspections/bulk-upload/", SiteInspectionBulkUploadView.as_view(), name="inspection-bulk-upload"),
    path("inspections/bulk-upload/template/", SiteInspectionBulkTemplateView.as_view(), name="inspection-bulk-template"),

    # Bulk upload — Subscriptions
    path("subscriptions/bulk-upload/", SubscriptionBulkUploadView.as_view(), name="subscription-bulk-upload"),
    path("subscriptions/bulk-upload/template/", SubscriptionBulkTemplateView.as_view(), name="subscription-bulk-template"),

    # Bulk upload — Installments
    path("installments/bulk-upload/", InstallmentBulkUploadView.as_view(), name="installment-bulk-upload"),
    path("installments/bulk-upload/template/", InstallmentBulkTemplateView.as_view(), name="installment-bulk-template"),
]
