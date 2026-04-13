"""
Commissions views — Sales reps and commission management.
"""

from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

_COMM_TAG = ["Commissions"]

from core.permissions import IsWorkspaceAdmin
from core.plan_guard import PlanGuard, PlanLimitExceeded
from commissions.models import Commission, SalesRep
from commissions.serializers import (
    CommissionSerializer,
    SalesRepCreateSerializer,
    SalesRepSerializer,
)
from commissions.services import CommissionService


# ---------------------------------------------------------------------------
# SalesRep endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_COMM_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_COMM_TAG))
class SalesRepListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/commissions/reps/
    POST /api/v1/commissions/reps/
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SalesRepCreateSerializer
        return SalesRepSerializer

    def get_queryset(self):
        return (
            SalesRep.objects.filter(workspace=self.request.workspace)
            .prefetch_related("commissions")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        try:
            PlanGuard.check_sales_rep_limit(self.request.workspace)
        except PlanLimitExceeded as e:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(str(e))
        serializer.save(workspace=self.request.workspace)


@method_decorator(name="retrieve",       decorator=swagger_auto_schema(tags=_COMM_TAG))
@method_decorator(name="update",         decorator=swagger_auto_schema(tags=_COMM_TAG))
@method_decorator(name="partial_update", decorator=swagger_auto_schema(tags=_COMM_TAG))
@method_decorator(name="destroy",        decorator=swagger_auto_schema(tags=_COMM_TAG))
class SalesRepDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/commissions/reps/<id>/"""

    serializer_class = SalesRepSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return SalesRep.objects.filter(
            workspace=self.request.workspace
        ).prefetch_related("commissions")


# ---------------------------------------------------------------------------
# Commission endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_COMM_TAG))
class CommissionListView(generics.ListAPIView):
    """
    GET /api/v1/commissions/

    List all commissions, filterable by status and sales_rep.
    """

    serializer_class = CommissionSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    filterset_fields = ["status", "sales_rep"]

    def get_queryset(self):
        return (
            Commission.objects.filter(workspace=self.request.workspace)
            .select_related("sales_rep", "payment")
            .order_by("-created_at")
        )


class CommissionMarkPaidView(APIView):
    """
    POST /api/v1/commissions/<id>/mark-paid/

    Mark a pending commission as paid.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(
        tags=_COMM_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "notes": openapi.Schema(
                    type=openapi.TYPE_STRING, description="Payout notes"
                ),
            },
        ),
        responses={200: CommissionSerializer},
        operation_description="Mark a pending commission as paid.",
    )
    def post(self, request, id):
        try:
            commission = Commission.objects.get(id=id, workspace=request.workspace)
        except Commission.DoesNotExist:
            return Response(
                {"message": "Commission not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        notes = request.data.get("notes", "")

        try:
            commission = CommissionService.mark_as_paid(commission, notes)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(CommissionSerializer(commission).data)
