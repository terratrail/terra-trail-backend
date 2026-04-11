"""
Core views — Workspace management endpoints.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import WorkspaceMembership
from core.models import Workspace
from core.serializers import (
    WorkspaceCreateSerializer,
    WorkspaceMinimalSerializer,
    WorkspaceSerializer,
)


class WorkspaceCreateView(generics.CreateAPIView):
    """
    POST /api/v1/workspaces/create/

    Creates a new workspace and assigns the requesting user as OWNER.
    """

    serializer_class = WorkspaceCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        workspace = serializer.save()
        # Make the creator the workspace owner
        WorkspaceMembership.objects.create(
            user=self.request.user,
            workspace=workspace,
            role="OWNER",
            is_active=True,
        )


class MyWorkspacesView(APIView):
    """
    GET /api/v1/workspaces/mine/

    Lists all workspaces the authenticated user belongs to.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = WorkspaceMembership.objects.filter(
            user=request.user, is_active=True
        ).select_related("workspace")

        workspaces = []
        for membership in memberships:
            ws = membership.workspace
            ws.role = membership.role  # Attach role for serialization
            workspaces.append(ws)

        serializer = WorkspaceMinimalSerializer(workspaces, many=True)
        return Response(serializer.data)


class WorkspaceDetailView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/workspaces/detail/

    Retrieve or update the current workspace.
    Requires workspace context (X-Workspace header).
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.workspace
