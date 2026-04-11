"""
Properties URL configuration.
"""

from django.urls import path
from properties.views import (
    BankAccountDetailView,
    BankAccountListCreateView,
    PricingPlanActivateView,
    PricingPlanDeactivateView,
    PricingPlanDetailView,
    PricingPlanListCreateView,
    PropertyDetailView,
    PropertyListCreateView,
    PropertyPublishView,
    PropertyUnpublishView,
)

app_name = "properties"

urlpatterns = [
    # Properties
    path("", PropertyListCreateView.as_view(), name="property-list-create"),
    path("<uuid:id>/", PropertyDetailView.as_view(), name="property-detail"),
    path("<uuid:id>/publish/", PropertyPublishView.as_view(), name="property-publish"),
    path("<uuid:id>/unpublish/", PropertyUnpublishView.as_view(), name="property-unpublish"),

    # Pricing Plans
    path("plans/", PricingPlanListCreateView.as_view(), name="plan-list-create"),
    path("plans/<uuid:id>/", PricingPlanDetailView.as_view(), name="plan-detail"),
    path("plans/<uuid:id>/activate/", PricingPlanActivateView.as_view(), name="plan-activate"),
    path("plans/<uuid:id>/deactivate/", PricingPlanDeactivateView.as_view(), name="plan-deactivate"),

    # Bank Accounts
    path("bank-accounts/", BankAccountListCreateView.as_view(), name="bank-list-create"),
    path("bank-accounts/<uuid:id>/", BankAccountDetailView.as_view(), name="bank-detail"),
]
