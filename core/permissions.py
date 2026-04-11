"""
Core permissions — Role-based access control.
"""

from rest_framework.permissions import BasePermission


class IsWorkspaceMember(BasePermission):
    """Allows access only to members of the current workspace."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace, is_active=True
        ).exists()


class IsWorkspaceOwner(BasePermission):
    """Allows access only to workspace owners."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace, role="OWNER", is_active=True
        ).exists()


class IsWorkspaceAdmin(BasePermission):
    """Allows access to workspace owners and admins."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role__in=["OWNER", "ADMIN"],
            is_active=True,
        ).exists()


class IsWorkspaceAdminOrReadOnly(BasePermission):
    """Admin/Owner can write; members can read."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.workspace_memberships.filter(
                workspace=request.workspace, is_active=True
            ).exists()

        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role__in=["OWNER", "ADMIN"],
            is_active=True,
        ).exists()


class IsSalesRep(BasePermission):
    """Allows access to sales representatives."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role="SALES_REP",
            is_active=True,
        ).exists()
