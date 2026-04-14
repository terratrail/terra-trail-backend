"""
Customer self-service portal URL configuration.

All endpoints are under /api/v1/portal/
"""

from django.urls import path
from customers.portal_views import (
    PortalMeView,
    PortalOTPRequestView,
    PortalOTPVerifyView,
    PortalRecordPaymentView,
    PortalSubscriptionDetailView,
    PortalSubscriptionListView,
)

app_name = "portal"

urlpatterns = [
    # Auth
    path("auth/request-otp/", PortalOTPRequestView.as_view(), name="portal-otp-request"),
    path("auth/verify-otp/",  PortalOTPVerifyView.as_view(),  name="portal-otp-verify"),

    # Data (require PortalToken auth)
    path("me/",                          PortalMeView.as_view(),                 name="portal-me"),
    path("subscriptions/",               PortalSubscriptionListView.as_view(),   name="portal-subscription-list"),
    path("subscriptions/<uuid:id>/",     PortalSubscriptionDetailView.as_view(), name="portal-subscription-detail"),
    path("payments/",                    PortalRecordPaymentView.as_view(),      name="portal-payment-record"),
]
