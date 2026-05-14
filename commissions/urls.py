"""
Commissions URL configuration.
"""

from django.urls import path
from commissions.views import (
    CommissionListView,
    CommissionMarkPaidView,
    MyRepCommissionsView,
    MyRepStatsView,
    SalesRepDetailView,
    SalesRepListCreateView,
)
from commissions.bulk_upload_views import (
    SalesRepBulkUploadView,
    SalesRepBulkTemplateView,
    CustomerRepBulkUploadView,
    CustomerRepBulkTemplateView,
)

app_name = "commissions"

urlpatterns = [
    # Sales Reps
    path("reps/", SalesRepListCreateView.as_view(), name="rep-list-create"),
    path("reps/<uuid:id>/", SalesRepDetailView.as_view(), name="rep-detail"),

    # Commissions
    path("", CommissionListView.as_view(), name="commission-list"),
    path("<uuid:id>/mark-paid/", CommissionMarkPaidView.as_view(), name="commission-mark-paid"),

    # Sales rep self-service
    path("my-stats/", MyRepStatsView.as_view(), name="my-rep-stats"),
    path("my-commissions/", MyRepCommissionsView.as_view(), name="my-rep-commissions"),

    # Bulk upload — Sales Reps
    path("reps/bulk-upload/", SalesRepBulkUploadView.as_view(), name="rep-bulk-upload"),
    path("reps/bulk-upload/template/", SalesRepBulkTemplateView.as_view(), name="rep-bulk-template"),

    # Bulk upload — Customer Reps
    path("customer-reps/bulk-upload/", CustomerRepBulkUploadView.as_view(), name="customer-rep-bulk-upload"),
    path("customer-reps/bulk-upload/template/", CustomerRepBulkTemplateView.as_view(), name="customer-rep-bulk-template"),
]
