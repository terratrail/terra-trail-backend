"""
Core URL configuration.
"""

from django.urls import path
from core.views import WorkspaceCreateView, MyWorkspacesView, WorkspaceDetailView

app_name = "core"

urlpatterns = [
    path("create/", WorkspaceCreateView.as_view(), name="workspace-create"),
    path("mine/", MyWorkspacesView.as_view(), name="workspace-list"),
    path("detail/", WorkspaceDetailView.as_view(), name="workspace-detail"),
]
