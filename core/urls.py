"""
Core URL configuration.
"""

from django.urls import path
from core.views import (
    WorkspaceCreateView, WorkspaceSlugCheckView, MyWorkspacesView, WorkspaceDetailView,
    WorkspaceSettingsView, WorkspaceActivityListView, WorkspaceMembersListView,
    InviteMemberView, InviteDetailView, AcceptInviteView, MyMembershipView,
    PlanListView, SelectPlanView, PlanUsageView, WorkspaceEventsView,
    WorkspaceMemberDetailView,
)

app_name = "core"

urlpatterns = [
    path("create/", WorkspaceCreateView.as_view(), name="workspace-create"),
    path("check-slug/", WorkspaceSlugCheckView.as_view(), name="workspace-check-slug"),
    path("mine/", MyWorkspacesView.as_view(), name="workspace-list"),
    path("detail/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("settings/", WorkspaceSettingsView.as_view(), name="workspace-settings"),
    path("activity/", WorkspaceActivityListView.as_view(), name="workspace-activity"),
    path("members/", WorkspaceMembersListView.as_view(), name="workspace-members"),
    path("members/<str:pk>/", WorkspaceMemberDetailView.as_view(), name="workspace-member-detail"),
    path("my-membership/", MyMembershipView.as_view(), name="workspace-my-membership"),
    path("invites/", InviteMemberView.as_view(), name="workspace-invites"),
    path("invites/<str:token>/", InviteDetailView.as_view(), name="workspace-invite-detail"),
    path("invites/<str:token>/accept/", AcceptInviteView.as_view(), name="workspace-invite-accept"),

    # Billing
    path("billing/plans/", PlanListView.as_view(), name="billing-plans"),
    path("billing/select/", SelectPlanView.as_view(), name="billing-select"),
    path("billing/usage/", PlanUsageView.as_view(), name="billing-usage"),

    # Notification events
    path("events/", WorkspaceEventsView.as_view(), name="workspace-events"),
]
