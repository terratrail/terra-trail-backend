"""
Notifications views — Notification logs and dashboard API.
"""

from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from customers.models import Installment, Subscription
from payments.models import Payment
from commissions.models import Commission, SalesRep
from notifications.models import NotificationLog
from notifications.serializers import NotificationLogSerializer


class NotificationLogListView(generics.ListAPIView):
    """
    GET /api/v1/notifications/

    List notification logs, filterable by type and status.
    """

    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    filterset_fields = ["notification_type", "status"]

    def get_queryset(self):
        return (
            NotificationLog.objects.filter(workspace=self.request.workspace)
            .order_by("-created_at")
        )


# ---------------------------------------------------------------------------
# Dashboard APIs
# ---------------------------------------------------------------------------


class DashboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/

    Returns key metrics for the workspace dashboard:
    - Total revenue (approved payments)
    - Outstanding balance
    - Active subscriptions
    - Customer count
    - Overdue installments
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get(self, request):
        workspace = request.workspace

        # Revenue (sum of approved payments)
        revenue = Payment.objects.filter(
            workspace=workspace,
            status=Payment.Status.APPROVED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Outstanding balance
        outstanding = Subscription.objects.filter(
            workspace=workspace,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.PENDING],
        ).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")

        # Counts
        active_subscriptions = Subscription.objects.filter(
            workspace=workspace,
            status=Subscription.Status.ACTIVE,
        ).count()

        total_customers = Subscription.objects.filter(
            workspace=workspace,
        ).values("customer").distinct().count()

        overdue_installments = Installment.objects.filter(
            workspace=workspace,
            status=Installment.Status.OVERDUE,
        ).count()

        pending_payments = Payment.objects.filter(
            workspace=workspace,
            status=Payment.Status.PENDING,
        ).count()

        pending_commissions = Commission.objects.filter(
            workspace=workspace,
            status=Commission.Status.PENDING,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return Response({
            "revenue": str(revenue),
            "outstanding_balance": str(outstanding),
            "active_subscriptions": active_subscriptions,
            "total_customers": total_customers,
            "overdue_installments": overdue_installments,
            "pending_payments": pending_payments,
            "pending_commissions": str(pending_commissions),
        })


class LeaderboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/leaderboard/

    Returns sales rep leaderboard ranked by total approved commission.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get(self, request):
        workspace = request.workspace

        reps = (
            SalesRep.objects.filter(workspace=workspace, is_active=True)
            .annotate(
                total_earned=Sum(
                    "commissions__amount",
                    filter=Q(commissions__status=Commission.Status.PAID),
                ),
                total_pending=Sum(
                    "commissions__amount",
                    filter=Q(commissions__status=Commission.Status.PENDING),
                ),
                total_referrals=Count("commissions"),
            )
            .order_by("-total_earned")[:20]
        )

        leaderboard = [
            {
                "id": str(rep.id),
                "name": rep.name,
                "tier": rep.tier,
                "referral_code": rep.referral_code,
                "total_earned": str(rep.total_earned or Decimal("0.00")),
                "total_pending": str(rep.total_pending or Decimal("0.00")),
                "total_referrals": rep.total_referrals,
            }
            for rep in reps
        ]

        return Response({"leaderboard": leaderboard})


class RevenueBreakdownView(APIView):
    """
    GET /api/v1/notifications/dashboard/revenue/

    Revenue breakdown by property.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def get(self, request):
        workspace = request.workspace

        breakdown = (
            Payment.objects.filter(
                workspace=workspace,
                status=Payment.Status.APPROVED,
            )
            .values(
                property_name=F("installment__subscription__property__name"),
            )
            .annotate(
                total_revenue=Sum("amount"),
                payment_count=Count("id"),
            )
            .order_by("-total_revenue")
        )

        return Response({
            "breakdown": [
                {
                    "property": item["property_name"],
                    "total_revenue": str(item["total_revenue"]),
                    "payment_count": item["payment_count"],
                }
                for item in breakdown
            ]
        })
