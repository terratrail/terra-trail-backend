"""
Properties views — CRUD and status management endpoints.
"""

from django.db.models import Count
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from properties.models import BankAccount, PricingPlan, Property
from properties.serializers import (
    BankAccountSerializer,
    PricingPlanCreateSerializer,
    PricingPlanSerializer,
    PropertyCreateSerializer,
    PropertyDetailSerializer,
    PropertyListSerializer,
)
from properties.services import PricingPlanService, PropertyService


# ---------------------------------------------------------------------------
# Property endpoints
# ---------------------------------------------------------------------------


class PropertyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/          — List properties
    POST /api/v1/properties/          — Create a property
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PropertyCreateSerializer
        return PropertyListSerializer

    def get_queryset(self):
        return (
            Property.objects.filter(workspace=self.request.workspace)
            .select_related("location")
            .annotate(pricing_plans_count=Count("pricing_plans"))
            .order_by("-created_at")
        )


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PATCH/DELETE /api/v1/properties/<id>/
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return PropertyCreateSerializer
        return PropertyDetailSerializer

    def get_queryset(self):
        return (
            Property.objects.filter(workspace=self.request.workspace)
            .select_related("location")
            .prefetch_related("pricing_plans", "bank_accounts")
        )


class PropertyPublishView(APIView):
    """POST /api/v1/properties/<id>/publish/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request, id):
        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            PropertyService.publish(prop)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Property published.", "status": prop.status})


class PropertyUnpublishView(APIView):
    """POST /api/v1/properties/<id>/unpublish/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request, id):
        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        PropertyService.unpublish(prop)
        return Response({"detail": "Property unpublished.", "status": prop.status})


# ---------------------------------------------------------------------------
# PricingPlan endpoints
# ---------------------------------------------------------------------------


class PricingPlanListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/plans/          — List all plans
    POST /api/v1/properties/plans/          — Create a plan
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PricingPlanCreateSerializer
        return PricingPlanSerializer

    def get_queryset(self):
        qs = PricingPlan.objects.filter(workspace=self.request.workspace)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs.select_related("property").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


class PricingPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/properties/plans/<id>/"""

    serializer_class = PricingPlanSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PricingPlan.objects.filter(workspace=self.request.workspace)


class PricingPlanActivateView(APIView):
    """POST /api/v1/properties/plans/<id>/activate/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request, id):
        try:
            plan = PricingPlan.objects.get(id=id, workspace=request.workspace)
        except PricingPlan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        PricingPlanService.activate(plan)
        return Response({"detail": "Plan activated."})


class PricingPlanDeactivateView(APIView):
    """POST /api/v1/properties/plans/<id>/deactivate/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def post(self, request, id):
        try:
            plan = PricingPlan.objects.get(id=id, workspace=request.workspace)
        except PricingPlan.DoesNotExist:
            return Response({"detail": "Plan not found."}, status=status.HTTP_404_NOT_FOUND)

        PricingPlanService.deactivate(plan)
        return Response({"detail": "Plan deactivated."})


# ---------------------------------------------------------------------------
# BankAccount endpoints
# ---------------------------------------------------------------------------


class BankAccountListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/bank-accounts/
    POST /api/v1/properties/bank-accounts/
    """

    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def get_queryset(self):
        qs = BankAccount.objects.filter(workspace=self.request.workspace)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/properties/bank-accounts/<id>/"""

    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return BankAccount.objects.filter(workspace=self.request.workspace)
