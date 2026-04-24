"""
Payments URL configuration.
"""

from django.urls import path
from payments.views import (
    ApprovePaymentView,
    PaymentDetailView,
    PaymentListView,
    PaystackBanksListView,
    RecordPaymentView,
    RejectPaymentView,
    ResolveAccountView,
)

app_name = "payments"

urlpatterns = [
    path("", PaymentListView.as_view(), name="payment-list"),
    path("record/", RecordPaymentView.as_view(), name="payment-record"),
    path("<uuid:id>/", PaymentDetailView.as_view(), name="payment-detail"),
    path("<uuid:id>/approve/", ApprovePaymentView.as_view(), name="payment-approve"),
    path("<uuid:id>/reject/", RejectPaymentView.as_view(), name="payment-reject"),
    path("verify-account/", ResolveAccountView.as_view(), name="verify-account"),
    path("banks/", PaystackBanksListView.as_view(), name="banks-list"),
]
