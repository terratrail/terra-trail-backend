"""
Notifications URL configuration.
"""

from django.urls import path
from notifications.views import (
    CustomerLeaderboardView,
    DashboardView,
    LeaderboardView,
    NotificationLogListView,
    PropertyLeaderboardView,
    RevenueBreakdownView,
)

app_name = "notifications"

urlpatterns = [
    # Notification logs
    path("", NotificationLogListView.as_view(), name="notification-list"),

    # Dashboard — key metrics
    path("dashboard/",              DashboardView.as_view(),            name="dashboard"),

    # Dashboard — leaderboards & breakdowns
    path("dashboard/leaderboard/",  LeaderboardView.as_view(),          name="leaderboard"),
    path("dashboard/revenue/",      RevenueBreakdownView.as_view(),     name="revenue-breakdown"),
    path("dashboard/properties/",   PropertyLeaderboardView.as_view(),  name="property-leaderboard"),
    path("dashboard/customers/",    CustomerLeaderboardView.as_view(),  name="customer-leaderboard"),
]
