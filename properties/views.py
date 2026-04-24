"""
Properties views — CRUD and status management endpoints.
"""

from django.db.models import Count
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from core.plan_guard import PlanGuard, PlanLimitExceeded
from properties.models import (
    BankAccount, PricingPlan, Property,
    PropertyAmenity, PropertyDocument, PropertyGallery,
)
from properties.serializers import (
    BankAccountSerializer,
    PricingPlanCreateSerializer,
    PricingPlanSerializer,
    PropertyAmenitySerializer,
    PropertyCreateSerializer,
    PropertyDetailSerializer,
    PropertyDocumentSerializer,
    PropertyGallerySerializer,
    PropertyListSerializer,
    PublicPropertySerializer,
)
from properties.services import PricingPlanService, PropertyService

_PROP_TAG = ["Properties"]


# ---------------------------------------------------------------------------
# Property endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/  — List properties
    POST /api/v1/properties/  — Create a property (all stepper fields accepted)
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

    def perform_create(self, serializer):
        try:
            PlanGuard.check_property_limit(self.request.workspace)
        except PlanLimitExceeded as e:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(str(e))
        serializer.save(workspace=self.request.workspace)


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/<id>/"""

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
            .prefetch_related(
                "pricing_plans", "bank_accounts",
                "amenities", "documents", "gallery_images",
            )
        )


class PropertyPublishView(APIView):
    """POST /api/v1/properties/<id>/publish/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(
        tags=_PROP_TAG,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "message": openapi.Schema(type=openapi.TYPE_STRING),
                "status":  openapi.Schema(type=openapi.TYPE_STRING),
            },
        )},
    )
    def post(self, request, id):
        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response(
                {"message": "Property not found."}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            PropertyService.publish(prop)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Property published.", "status": prop.status})


class PropertyUnpublishView(APIView):
    """POST /api/v1/properties/<id>/unpublish/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(
        tags=_PROP_TAG,
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={"message": openapi.Schema(type=openapi.TYPE_STRING)},
        )},
    )
    def post(self, request, id):
        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response(
                {"message": "Property not found."}, status=status.HTTP_404_NOT_FOUND
            )

        PropertyService.unpublish(prop)
        return Response({"message": "Property unpublished.", "status": prop.status})


# ---------------------------------------------------------------------------
# PricingPlan endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
class PricingPlanListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/plans/  — List all plans
    POST /api/v1/properties/plans/  — Create a plan
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


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class PricingPlanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/plans/<id>/"""

    serializer_class = PricingPlanSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PricingPlan.objects.filter(workspace=self.request.workspace)


class PricingPlanActivateView(APIView):
    """POST /api/v1/properties/plans/<id>/activate/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=_PROP_TAG)
    def post(self, request, id):
        try:
            plan = PricingPlan.objects.get(id=id, workspace=request.workspace)
        except PricingPlan.DoesNotExist:
            return Response(
                {"message": "Plan not found."}, status=status.HTTP_404_NOT_FOUND
            )

        PricingPlanService.activate(plan)
        return Response({"message": "Plan activated."})


class PricingPlanDeactivateView(APIView):
    """POST /api/v1/properties/plans/<id>/deactivate/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=_PROP_TAG)
    def post(self, request, id):
        try:
            plan = PricingPlan.objects.get(id=id, workspace=request.workspace)
        except PricingPlan.DoesNotExist:
            return Response(
                {"message": "Plan not found."}, status=status.HTTP_404_NOT_FOUND
            )

        PricingPlanService.deactivate(plan)
        return Response({"message": "Plan deactivated."})


# ---------------------------------------------------------------------------
# BankAccount endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
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


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/bank-accounts/<id>/"""

    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]
    lookup_field = "id"

    def get_queryset(self):
        return BankAccount.objects.filter(workspace=self.request.workspace)


# ---------------------------------------------------------------------------
# PropertyAmenity endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyAmenityListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/amenities/?property_id=<uuid>  — List amenities
    POST /api/v1/properties/amenities/                      — Add an amenity
    """

    serializer_class = PropertyAmenitySerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_queryset(self):
        qs = PropertyAmenity.objects.filter(workspace=self.request.workspace)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs.select_related("property").order_by("name")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyAmenityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/amenities/<id>/"""

    serializer_class = PropertyAmenitySerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PropertyAmenity.objects.filter(workspace=self.request.workspace)


# ---------------------------------------------------------------------------
# PropertyDocument endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyDocumentListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/documents/?property_id=<uuid>  — List documents
    POST /api/v1/properties/documents/                      — Add a document
    """

    serializer_class = PropertyDocumentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_queryset(self):
        qs = PropertyDocument.objects.filter(workspace=self.request.workspace)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs.select_related("property").order_by("document_type")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyDocumentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/documents/<id>/"""

    serializer_class = PropertyDocumentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PropertyDocument.objects.filter(workspace=self.request.workspace)


# ---------------------------------------------------------------------------
# PropertyGallery endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list",   decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyGalleryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/properties/gallery/?property_id=<uuid>  — List gallery images
    POST /api/v1/properties/gallery/                      — Upload a gallery image
    """

    serializer_class = PropertyGallerySerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_queryset(self):
        qs = PropertyGallery.objects.filter(workspace=self.request.workspace)
        property_id = self.request.query_params.get("property_id")
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs.select_related("property").order_by("order", "created_at")

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


@method_decorator(name="retrieve",      decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="update",        decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="partial_update",decorator=swagger_auto_schema(tags=_PROP_TAG))
@method_decorator(name="destroy",       decorator=swagger_auto_schema(tags=_PROP_TAG))
class PropertyGalleryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/properties/gallery/<id>/"""

    serializer_class = PropertyGallerySerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return PropertyGallery.objects.filter(workspace=self.request.workspace)


# ---------------------------------------------------------------------------
# Public (unauthenticated) endpoints
# ---------------------------------------------------------------------------


class PublicPropertyListView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/properties/
    No auth required — returns PUBLISHED properties for the workspace.
    """

    permission_classes = []

    def get(self, request, workspace_slug):
        from core.models import Workspace
        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = (
            Property.objects.filter(workspace=workspace, status="PUBLISHED")
            .select_related("location")
            .prefetch_related("pricing_plans", "gallery_images", "amenities")
            .order_by("-created_at")
        )
        return Response(PublicPropertySerializer(qs, many=True, context={"request": request}).data)


class PublicPropertyDetailView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/properties/<id>/
    No auth required — returns a single PUBLISHED property.
    """

    permission_classes = []

    def get(self, request, workspace_slug, id):
        from core.models import Workspace
        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            prop = (
                Property.objects.filter(workspace=workspace, status="PUBLISHED")
                .select_related("location")
                .prefetch_related("pricing_plans", "gallery_images", "amenities")
                .get(id=id)
            )
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(PublicPropertySerializer(prop, context={"request": request}).data)


# ---------------------------------------------------------------------------
# Inspection Config endpoints
# ---------------------------------------------------------------------------

class InspectionConfigView(APIView):
    """
    GET  /api/v1/properties/<id>/inspection-config/  — Get config (or 404)
    POST /api/v1/properties/<id>/inspection-config/  — Create or update config
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def _get_property(self, request, id):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Property, id=id, workspace=request.workspace)

    def get(self, request, id):
        from properties.models import InspectionConfig
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        try:
            config = prop.inspection_config
        except InspectionConfig.DoesNotExist:
            return Response({}, status=status.HTTP_200_OK)
        return Response(InspectionConfigSerializer(config, context={"request": request}).data)

    def post(self, request, id):
        from properties.models import InspectionConfig
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        try:
            config = prop.inspection_config
            serializer = InspectionConfigSerializer(config, data=request.data, partial=True, context={"request": request})
        except InspectionConfig.DoesNotExist:
            data = {**request.data, "property": str(prop.id)}
            serializer = InspectionConfigSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save(workspace=request.workspace, property=prop)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicInspectionConfigView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/properties/<id>/inspection-config/
    Public — no auth required.
    """
    permission_classes = []

    def get(self, request, workspace_slug, id):
        from core.models import Workspace
        from properties.models import InspectionConfig
        from properties.serializers import InspectionConfigSerializer
        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            prop = Property.objects.get(id=id, workspace=workspace, status="PUBLISHED")
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            config = prop.inspection_config
            return Response(InspectionConfigSerializer(config, context={"request": request}).data)
        except InspectionConfig.DoesNotExist:
            return Response({}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Property Appreciation endpoints
# ---------------------------------------------------------------------------

class PropertyAppreciationListCreateView(APIView):
    """
    GET  /api/v1/properties/<id>/appreciations/  — List appreciation records
    POST /api/v1/properties/<id>/appreciations/  — Add an appreciation record
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def _get_property(self, request, id):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Property, id=id, workspace=request.workspace)

    def get(self, request, id):
        from properties.models import PropertyAppreciation
        from properties.serializers import PropertyAppreciationSerializer
        prop = self._get_property(request, id)
        qs = PropertyAppreciation.objects.filter(workspace=request.workspace, property=prop)
        return Response(PropertyAppreciationSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request, id):
        from properties.models import PropertyAppreciation
        from properties.serializers import PropertyAppreciationSerializer
        prop = self._get_property(request, id)
        data = {**request.data, "property": str(prop.id)}
        serializer = PropertyAppreciationSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save(workspace=request.workspace, property=prop)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PropertyAppreciationDetailView(APIView):
    """DELETE /api/v1/properties/<id>/appreciations/<appr_id>/"""
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def delete(self, request, id, appr_id):
        from properties.models import PropertyAppreciation
        try:
            obj = PropertyAppreciation.objects.get(id=appr_id, workspace=request.workspace, property_id=id)
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PropertyAppreciation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


class PublicPropertyAppreciationView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/properties/<id>/appreciations/
    Public — no auth required.
    """
    permission_classes = []

    def get(self, request, workspace_slug, id):
        from core.models import Workspace
        from properties.models import PropertyAppreciation
        from properties.serializers import PropertyAppreciationSerializer
        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            Property.objects.get(id=id, workspace=workspace, status="PUBLISHED")
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)
        qs = PropertyAppreciation.objects.filter(workspace=workspace, property_id=id)
        return Response(PropertyAppreciationSerializer(qs, many=True, context={"request": request}).data)
