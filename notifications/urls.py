"""
Notifications URL configuration.
"""

from django.urls import path
from notifications.views import (
    DashboardView,
    LeaderboardView,
    NotificationLogListView,
    RevenueBreakdownView,
)

app_name = "notifications"

urlpatterns = [
    # Notification logs
    path("", NotificationLogListView.as_view(), name="notification-list"),

    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("dashboard/revenue/", RevenueBreakdownView.as_view(), name="revenue-breakdown"),
]
