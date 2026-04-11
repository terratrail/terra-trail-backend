"""
Accounts URL configuration.
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.views import (
    AddMemberView,
    LoginView,
    MeView,
    OTPRequestView,
    OTPVerifyView,
    RegisterView,
    WorkspaceMembersView,
)

app_name = "accounts"

urlpatterns = [
    # JWT Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),

    # Customer Portal OTP
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),

    # Workspace Members (requires workspace context)
    path("members/", WorkspaceMembersView.as_view(), name="members-list"),
    path("members/add/", AddMemberView.as_view(), name="members-add"),
]
