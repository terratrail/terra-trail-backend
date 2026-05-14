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
        qs = (
            Commission.objects.filter(workspace=self.request.workspace)
            .select_related("sales_rep", "payment")
            .order_by("-created_at")
        )
        property_id = self.request.query_params.get("property")
        if property_id:
            qs = qs.filter(payment__installment__subscription__property=property_id)
        return qs


class MyRepStatsView(APIView):
    """GET /api/v1/commissions/my-stats/ — stats for the authenticated sales rep"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=_COMM_TAG)
    def get(self, request):
        from django.db.models import Sum

        try:
            rep = SalesRep.objects.get(
                email=request.user.email,
                workspace=request.workspace,
            )
        except SalesRep.DoesNotExist:
            return Response(
                {"detail": "Not a sales rep in this workspace."},
                status=404,
            )

        comms = Commission.objects.filter(sales_rep=rep, workspace=request.workspace)

        return Response(
            {
                "rep_id": str(rep.id),
                "name": rep.name,
                "email": rep.email,
                "phone": rep.phone,
                "tier": rep.tier,
                "referral_code": rep.referral_code,
                "commission_type": rep.commission_type,
                "commission_rate": str(rep.commission_rate),
                "bank_name": rep.bank_name,
                "bank_account_number": rep.bank_account_number,
                "bank_account_name": rep.bank_account_name,
                "total_earned": str(
                    comms.filter(status="PAID").aggregate(t=Sum("amount"))["t"] or 0
                ),
                "total_pending": str(
                    comms.filter(status="PENDING").aggregate(t=Sum("amount"))["t"] or 0
                ),
                "total_commissions": comms.count(),
                "total_referrals": comms.values("payment__installment__subscription").distinct().count(),
            }
        )


class MyRepCommissionsView(APIView):
    """GET /api/v1/commissions/my-commissions/ — paginated commissions for the authenticated sales rep"""

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(tags=_COMM_TAG)
    def get(self, request):
        try:
            rep = SalesRep.objects.get(
                email=request.user.email,
                workspace=request.workspace,
            )
        except SalesRep.DoesNotExist:
            return Response(
                {"detail": "Not a sales rep in this workspace."},
                status=404,
            )

        comms = (
            Commission.objects.filter(sales_rep=rep, workspace=request.workspace)
            .select_related("payment__installment__subscription__property")
            .order_by("-created_at")
        )

        # Simple pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except (TypeError, ValueError):
            page, page_size = 1, 20

        total = comms.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = comms[start:end]

        results = []
        for c in page_qs:
            try:
                property_name = c.payment.installment.subscription.property.name
            except Exception:
                property_name = "—"
            results.append(
                {
                    "id": str(c.id),
                    "property_name": property_name,
                    "amount": str(c.amount),
                    "status": c.status,
                    "paid_date": c.paid_date,
                    "created_at": c.created_at.isoformat(),
                }
            )

        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "page_count": max(1, -(-total // page_size)),  # ceiling division
                "results": results,
            }
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
