"""
Customers URL configuration.
"""

from django.urls import path
from customers.views import (
    CustomerDetailView,
    CustomerListCreateView,
    InstallmentListView,
    SubscriptionCreateView,
    SubscriptionDetailView,
    SubscriptionListView,
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

    # Installments
    path("installments/", InstallmentListView.as_view(), name="installment-list"),
]
