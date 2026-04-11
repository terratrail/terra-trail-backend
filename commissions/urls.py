"""
Commissions URL configuration.
"""

from django.urls import path
from commissions.views import (
    CommissionListView,
    CommissionMarkPaidView,
    SalesRepDetailView,
    SalesRepListCreateView,
)

app_name = "commissions"

urlpatterns = [
    # Sales Reps
    path("reps/", SalesRepListCreateView.as_view(), name="rep-list-create"),
    path("reps/<uuid:id>/", SalesRepDetailView.as_view(), name="rep-detail"),

    # Commissions
    path("", CommissionListView.as_view(), name="commission-list"),
    path("<uuid:id>/mark-paid/", CommissionMarkPaidView.as_view(), name="commission-mark-paid"),
]
