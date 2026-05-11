"""
Notifications views — Notification logs and dashboard API.
"""

from datetime import date
from decimal import Decimal
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
from django.utils.decorators import method_decorator
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

_NOTIF_TAG = ["Notifications"]

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from customers.models import Customer, Installment, Subscription
from payments.models import Payment
from commissions.models import Commission, SalesRep
from notifications.models import NotificationLog
from notifications.serializers import NotificationLogSerializer


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_NOTIF_TAG))
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
# Dashboard helpers
# ---------------------------------------------------------------------------

def _parse_date_params(request):
    """
    Parse optional date_from / date_to query params.
    Returns (date_from, date_to) — either may be None.
    """
    date_from = request.query_params.get("date_from")
    date_to   = request.query_params.get("date_to")
    try:
        date_from = date.fromisoformat(date_from) if date_from else None
        date_to   = date.fromisoformat(date_to)   if date_to   else None
    except ValueError:
        date_from = date_to = None
    return date_from, date_to


def _apply_date_filter(qs, field, date_from, date_to):
    """Apply optional date range filter to a queryset."""
    if date_from:
        qs = qs.filter(**{f"{field}__date__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__date__lte": date_to})
    return qs


_DATE_PARAMS = [
    openapi.Parameter(
        "date_from", openapi.IN_QUERY,
        description="Filter from date (ISO 8601, e.g. 2026-01-01). Affects revenue, commissions, and leaderboards.",
        type=openapi.TYPE_STRING, required=False,
    ),
    openapi.Parameter(
        "date_to", openapi.IN_QUERY,
        description="Filter to date (ISO 8601, e.g. 2026-12-31). Affects revenue, commissions, and leaderboards.",
        type=openapi.TYPE_STRING, required=False,
    ),
]


# ---------------------------------------------------------------------------
# Dashboard — Key Metrics
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/

    Key metrics for the workspace dashboard.

    Date-filtered fields (affected by date_from / date_to):
      - revenue, net_revenue
      - commission_earned, commission_pending (within the date range)

    Always-current fields (not date-filtered per PRD 5.7):
      - outstanding_balance, potential_revenue
      - active_subscriptions, total_customers, overdue_installments
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    @swagger_auto_schema(tags=_NOTIF_TAG, manual_parameters=_DATE_PARAMS)
    def get(self, request):
        workspace = request.workspace
        date_from, date_to = _parse_date_params(request)

        # ---- Date-filtered: Revenue (approved payments) -------------------
        revenue_qs = Payment.objects.filter(workspace=workspace, status=Payment.Status.APPROVED)
        revenue_qs = _apply_date_filter(revenue_qs, "created_at", date_from, date_to)
        revenue = revenue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # ---- Date-filtered: Commissions -----------------------------------
        comm_qs = Commission.objects.filter(workspace=workspace)
        comm_qs_dated = _apply_date_filter(comm_qs, "created_at", date_from, date_to)

        commission_earned = (
            comm_qs_dated.filter(status=Commission.Status.PAID)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )
        commission_pending = (
            comm_qs_dated.filter(status=Commission.Status.PENDING)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )
        # Potential commission = all pending + paid (what would have been earned across date range)
        commission_potential = (
            comm_qs_dated
            .exclude(status=Commission.Status.CANCELLED)
            .aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        )

        # ---- Net revenue (date-filtered revenue minus date-filtered commissions paid) ---
        net_revenue = revenue - commission_earned

        # ---- Always-current: balances & counts ----------------------------
        outstanding = (
            Subscription.objects.filter(
                workspace=workspace,
                status__in=[Subscription.Status.ACTIVE, Subscription.Status.PENDING],
            ).aggregate(total=Sum("balance"))["total"] or Decimal("0.00")
        )

        # Potential revenue = total_price of all non-cancelled subscriptions
        potential_revenue = (
            Subscription.objects.filter(workspace=workspace)
            .exclude(status=Subscription.Status.CANCELLED)
            .aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")
        )

        active_subscriptions = Subscription.objects.filter(
            workspace=workspace, status=Subscription.Status.ACTIVE
        ).count()

        completed_subscriptions = Subscription.objects.filter(
            workspace=workspace, status=Subscription.Status.COMPLETED
        ).count()

        defaulting_subscriptions = Subscription.objects.filter(
            workspace=workspace, status=Subscription.Status.DEFAULTING
        ).count()

        # Allocation stats (from completed subscriptions)
        pending_allocation = Subscription.objects.filter(
            workspace=workspace,
            status=Subscription.Status.COMPLETED,
            plot_number="",
        ).count()

        allocated = Subscription.objects.filter(
            workspace=workspace,
            status=Subscription.Status.COMPLETED,
        ).exclude(plot_number="").count()

        total_customers = (
            Customer.objects.filter(workspace=workspace).count()
        )

        overdue_installments = Installment.objects.filter(
            workspace=workspace, status=Installment.Status.OVERDUE
        ).count()

        pending_payments = Payment.objects.filter(
            workspace=workspace, status=Payment.Status.PENDING
        ).count()

        from properties.models import Property
        total_properties = Property.objects.filter(workspace=workspace).count()

        return Response({
            # Date-filtered financial
            "revenue":              str(revenue),
            "net_revenue":          str(net_revenue),
            # Always-current financial
            "outstanding_balance":  str(outstanding),
            "potential_revenue":    str(potential_revenue),
            # Commission breakdown
            "commission_earned":    str(commission_earned),
            "commission_pending":   str(commission_pending),
            "commission_potential": str(commission_potential),
            # Counts (always-current)
            "active_subscriptions":   active_subscriptions,
            "completed_subscriptions": completed_subscriptions,
            "defaulting_subscriptions": defaulting_subscriptions,
            "pending_allocation":     pending_allocation,
            "allocated":              allocated,
            "total_customers":        total_customers,
            "total_properties":       total_properties,
            "overdue_installments":   overdue_installments,
            "pending_payments":       pending_payments,
            # Applied filters (echo back for UI awareness)
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to":   date_to.isoformat()   if date_to   else None,
            },
        })


# ---------------------------------------------------------------------------
# Dashboard — Sales Rep Leaderboard
# ---------------------------------------------------------------------------

class LeaderboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/leaderboard/

    Sales rep leaderboard ranked by total approved commission.
    Supports date_from / date_to filtering.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    @swagger_auto_schema(tags=_NOTIF_TAG, manual_parameters=_DATE_PARAMS)
    def get(self, request):
        workspace = request.workspace
        date_from, date_to = _parse_date_params(request)

        paid_filter   = Q(commissions__status=Commission.Status.PAID)
        pending_filter = Q(commissions__status=Commission.Status.PENDING)

        if date_from:
            paid_filter    &= Q(commissions__created_at__date__gte=date_from)
            pending_filter &= Q(commissions__created_at__date__gte=date_from)
        if date_to:
            paid_filter    &= Q(commissions__created_at__date__lte=date_to)
            pending_filter &= Q(commissions__created_at__date__lte=date_to)

        reps = (
            SalesRep.objects.filter(workspace=workspace, is_active=True)
            .annotate(
                total_earned=Coalesce(
                    Sum("commissions__amount", filter=paid_filter),
                    Decimal("0.00"),
                    output_field=DecimalField(),
                ),
                total_pending=Coalesce(
                    Sum("commissions__amount", filter=pending_filter),
                    Decimal("0.00"),
                    output_field=DecimalField(),
                ),
                total_referrals=Count("commissions", distinct=True),
            )
            .order_by("-total_earned")[:20]
        )

        return Response({
            "leaderboard": [
                {
                    "id":             str(rep.id),
                    "name":           rep.name,
                    "tier":           rep.tier,
                    "referral_code":  rep.referral_code,
                    "total_earned":   str(rep.total_earned),
                    "total_pending":  str(rep.total_pending),
                    "total_referrals": rep.total_referrals,
                }
                for rep in reps
            ],
        })


# ---------------------------------------------------------------------------
# Dashboard — Revenue Breakdown by Property
# ---------------------------------------------------------------------------

class RevenueBreakdownView(APIView):
    """
    GET /api/v1/notifications/dashboard/revenue/

    Revenue breakdown by property (approved payments).
    Supports date_from / date_to filtering.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=_NOTIF_TAG, manual_parameters=_DATE_PARAMS)
    def get(self, request):
        workspace = request.workspace
        date_from, date_to = _parse_date_params(request)

        qs = Payment.objects.filter(workspace=workspace, status=Payment.Status.APPROVED)
        qs = _apply_date_filter(qs, "created_at", date_from, date_to)

        breakdown = (
            qs.values(property_name=F("installment__subscription__property__name"))
            .annotate(total_revenue=Sum("amount"), payment_count=Count("id"))
            .order_by("-total_revenue")
        )

        return Response({
            "breakdown": [
                {
                    "property":       item["property_name"],
                    "total_revenue":  str(item["total_revenue"]),
                    "payment_count":  item["payment_count"],
                }
                for item in breakdown
            ],
        })


# ---------------------------------------------------------------------------
# Dashboard — Property Leaderboard
# ---------------------------------------------------------------------------

class PropertyLeaderboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/properties/

    Property analytics:
      - top_by_subscriptions: properties ranked by active subscription count
      - top_by_revenue: properties ranked by approved payment revenue

    Supports date_from / date_to filtering on revenue (subscription counts
    are always-current per PRD 5.7).
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    @swagger_auto_schema(tags=_NOTIF_TAG, manual_parameters=_DATE_PARAMS)
    def get(self, request):
        from properties.models import Property

        workspace = request.workspace
        date_from, date_to = _parse_date_params(request)

        # Top by active subscriptions (always-current count)
        top_by_subs = (
            Property.objects.filter(workspace=workspace)
            .annotate(
                subscription_count=Count(
                    "subscriptions",
                    filter=Q(subscriptions__status=Subscription.Status.ACTIVE),
                )
            )
            .order_by("-subscription_count")[:10]
        )

        # Top by revenue (date-filtered)
        revenue_filter = Q(
            subscriptions__installments__payments__status=Payment.Status.APPROVED
        )
        if date_from:
            revenue_filter &= Q(subscriptions__installments__payments__created_at__date__gte=date_from)
        if date_to:
            revenue_filter &= Q(subscriptions__installments__payments__created_at__date__lte=date_to)

        top_by_revenue = (
            Property.objects.filter(workspace=workspace)
            .annotate(
                total_revenue=Coalesce(
                    Sum(
                        "subscriptions__installments__payments__amount",
                        filter=revenue_filter,
                    ),
                    Decimal("0.00"),
                    output_field=DecimalField(),
                )
            )
            .order_by("-total_revenue")[:10]
        )

        return Response({
            "top_by_subscriptions": [
                {
                    "id":                 str(p.id),
                    "name":               p.name,
                    "subscription_count": p.subscription_count,
                }
                for p in top_by_subs
            ],
            "top_by_revenue": [
                {
                    "id":            str(p.id),
                    "name":          p.name,
                    "total_revenue": str(p.total_revenue),
                }
                for p in top_by_revenue
            ],
        })


# ---------------------------------------------------------------------------
# Dashboard — Customer Leaderboard
# ---------------------------------------------------------------------------

class CustomerLeaderboardView(APIView):
    """
    GET /api/v1/notifications/dashboard/customers/

    Customer analytics:
      - top_by_revenue: customers ranked by total amount paid
      - top_by_subscriptions: customers ranked by number of subscriptions

    Supports date_from / date_to filtering on revenue.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    @swagger_auto_schema(tags=_NOTIF_TAG, manual_parameters=_DATE_PARAMS)
    def get(self, request):
        workspace = request.workspace
        date_from, date_to = _parse_date_params(request)

        # Top by amount paid (date-filtered approved payments)
        revenue_filter = Q(
            subscriptions__installments__payments__status=Payment.Status.APPROVED
        )
        if date_from:
            revenue_filter &= Q(
                subscriptions__installments__payments__created_at__date__gte=date_from
            )
        if date_to:
            revenue_filter &= Q(
                subscriptions__installments__payments__created_at__date__lte=date_to
            )

        top_by_revenue = (
            Customer.objects.filter(workspace=workspace)
            .annotate(
                total_paid=Coalesce(
                    Sum(
                        "subscriptions__installments__payments__amount",
                        filter=revenue_filter,
                    ),
                    Decimal("0.00"),
                    output_field=DecimalField(),
                )
            )
            .order_by("-total_paid")[:10]
        )

        # Top by subscription count (always-current)
        top_by_subs = (
            Customer.objects.filter(workspace=workspace)
            .annotate(subscription_count=Count("subscriptions", distinct=True))
            .order_by("-subscription_count")[:10]
        )

        return Response({
            "top_by_revenue": [
                {
                    "id":         str(c.id),
                    "full_name":  c.full_name,
                    "email":      c.email,
                    "total_paid": str(c.total_paid),
                }
                for c in top_by_revenue
            ],
            "top_by_subscriptions": [
                {
                    "id":                 str(c.id),
                    "full_name":          c.full_name,
                    "email":              c.email,
                    "subscription_count": c.subscription_count,
                }
                for c in top_by_subs
            ],
        })
