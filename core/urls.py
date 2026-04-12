"""
Core URL configuration.
"""

from django.urls import path
from core.views import (
    WorkspaceCreateView, MyWorkspacesView, WorkspaceDetailView,
    WorkspaceSettingsView, WorkspaceActivityListView, WorkspaceMembersListView,
    InviteMemberView
)

app_name = "core"

urlpatterns = [
    path("create/", WorkspaceCreateView.as_view(), name="workspace-create"),
    path("mine/", MyWorkspacesView.as_view(), name="workspace-list"),
    path("detail/", WorkspaceDetailView.as_view(), name="workspace-detail"),
    path("settings/", WorkspaceSettingsView.as_view(), name="workspace-settings"),
    path("activity/", WorkspaceActivityListView.as_view(), name="workspace-activity"),
    path("members/", WorkspaceMembersListView.as_view(), name="workspace-members"),
    path("invites/", InviteMemberView.as_view(), name="workspace-invites"),
]
