"""
Core views — Workspace management endpoints.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema

from accounts.models import WorkspaceMembership
from core.models import Workspace, WorkspaceSettings, WorkspaceActivity
from core.serializers import (
    WorkspaceCreateSerializer,
    WorkspaceMinimalSerializer,
    WorkspaceSerializer,
    WorkspaceSettingsSerializer,
    WorkspaceActivitySerializer,
    WorkspaceInvitationSerializer,
)
from accounts.services import WorkspaceService
from accounts.serializers import WorkspaceMembershipSerializer


class WorkspaceCreateView(generics.CreateAPIView):
    """
    POST /api/v1/workspaces/create/

    Creates a new workspace and assigns the requesting user as OWNER.
    """

    serializer_class = WorkspaceCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Use service to ensure atomic creation, settings init, and logging
        workspace = WorkspaceService.create_workspace(
            user=self.request.user, **serializer.validated_data
        )
        serializer.instance = workspace


class MyWorkspacesView(APIView):
    """
    GET /api/v1/workspaces/mine/

    Lists all workspaces the authenticated user belongs to.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={200: WorkspaceMinimalSerializer(many=True)},
        operation_description="Lists all workspaces the authenticated user belongs to.",
    )
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

    Retrieve or update the current workspace general settings.
    Requires workspace context (X-Workspace header).
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.workspace


class WorkspaceSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH /api/v1/workspaces/settings/

    Retrieve or update granular permission and notification settings.
    """

    serializer_class = WorkspaceSettingsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return WorkspaceSettings.objects.get(workspace=self.request.workspace)
        except WorkspaceSettings.DoesNotExist:
            return WorkspaceSettings.objects.create(workspace=self.request.workspace)


class WorkspaceActivityListView(generics.ListAPIView):
    """
    GET /api/v1/workspaces/activity/

    List all activity logs for the current workspace.
    """

    serializer_class = WorkspaceActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WorkspaceActivity.objects.filter(workspace=self.request.workspace)
            .select_related("actor")
            .order_by("-created_at")
        )


class WorkspaceMembersListView(generics.ListAPIView):
    """
    GET /api/v1/workspaces/members/

    List all people (members) in the workspace with managed counts.
    """

    serializer_class = WorkspaceMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WorkspaceMembership.objects.filter(
                workspace=self.request.workspace, is_active=True
            )
            .select_related("user")
            .order_by("user__first_name")
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Add managed counts to each member
        data = serializer.data
        for item in data:
            user_id = item["user"]
            from customers.models import Customer, Subscription
            item["managed_customers_count"] = Customer.objects.filter(
                workspace=request.workspace, assigned_rep_id=user_id
            ).count()
            item["managed_subscriptions_count"] = Subscription.objects.filter(
                workspace=request.workspace, assigned_rep_id=user_id
            ).count()
            
        return Response(data)


class InviteMemberView(generics.CreateAPIView):
    """
    POST /api/v1/workspaces/invites/

    Create a new invitation to the workspace.
    """

    serializer_class = WorkspaceInvitationSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        import uuid
        from datetime import timedelta
        from django.utils import timezone
        
        token = str(uuid.uuid4())
        expiry = timezone.now() + timedelta(days=7)
        
        serializer.save(
            workspace=self.request.workspace,
            invited_by=self.request.user,
            token=token,
            expires_at=expiry
        )
        
        # Log activity
        WorkspaceActivity.objects.create(
            workspace=self.request.workspace,
            actor=self.request.user,
            action_text=f"generated an invite link for role '{serializer.validated_data['role']}'",
            category="Workspace"
        )


class WorkspaceHomeView(APIView):
    """
    GET /
    
    Renders the public landing page for the workspace.
    Uses the context injected by WorkspaceMiddleware.
    """
    
    permission_classes = [] # Allow public access to landing page
    
    def get(self, request):
        from django.shortcuts import render
        return render(request, "core/landing.html", {"workspace": request.workspace})
