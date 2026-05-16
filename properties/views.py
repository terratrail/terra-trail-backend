"""
Properties views — CRUD and status management endpoints.
"""

from django.db.models import Count, Min
from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from core.plan_guard import PlanGuard, PlanLimitExceeded
from properties.models import (
    BankAccount, PricingPlan, PricingPlanHistory, Property,
    PropertyAmenity, PropertyDocument, PropertyGallery,
)
from properties.serializers import (
    BankAccountSerializer,
    PricingPlanCreateSerializer,
    PricingPlanHistorySerializer,
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
            .prefetch_related("land_sizes", "pricing_plans")
            .annotate(
                pricing_plans_count=Count("pricing_plans", distinct=True),
                subscription_count=Count("subscriptions", distinct=True),
                price_from=Min("pricing_plans__total_price"),
            )
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
        property_id = self.request.data.get("property") or self.request.data.get("property_id")
        if not property_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"property": "Property ID is required."})
        try:
            prop = Property.objects.get(id=property_id, workspace=self.request.workspace)
        except Property.DoesNotExist:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"property": "Property not found."})
        serializer.save(workspace=self.request.workspace, property=prop)


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


class PublicWorkspaceInfoView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/info/
    No auth required — returns public workspace metadata.
    """

    permission_classes = [AllowAny]

    def get(self, request, workspace_slug):
        from core.models import Workspace
        try:
            ws = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=404)

        logo_url = None
        if ws.logo:
            try:
                logo_url = request.build_absolute_uri(ws.logo.url)
            except Exception:
                logo_url = None

        return Response({
            "id": str(ws.id),
            "name": ws.name,
            "slug": ws.slug,
            "logo": logo_url,
            "support_email": ws.support_email,
            "support_whatsapp": ws.support_whatsapp,
            "website_url": ws.website_url,
            "instagram_url": ws.instagram_url,
            "facebook_url": ws.facebook_url,
            "twitter_url": ws.twitter_url,
            "linkedin_url": ws.linkedin_url,
            "youtube_url": ws.youtube_url,
            "create_estate_public_pages": ws.create_estate_public_pages,
        })


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
                .prefetch_related("pricing_plans", "gallery_images", "amenities", "bank_accounts", "documents")
                .get(id=id)
            )
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(PublicPropertySerializer(prop, context={"request": request}).data)


# ---------------------------------------------------------------------------
# Inspection Config endpoints
# ---------------------------------------------------------------------------

class InspectionConfigListCreateView(APIView):
    """
    GET  /api/v1/properties/<id>/inspection-configs/  — List all configs for property
    POST /api/v1/properties/<id>/inspection-configs/  — Create a new config
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def _get_property(self, request, id):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Property, id=id, workspace=request.workspace)

    def get(self, request, id):
        from properties.models import InspectionConfig
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        configs = InspectionConfig.objects.filter(workspace=request.workspace, property=prop).order_by("-created_at")
        return Response(InspectionConfigSerializer(configs, many=True, context={"request": request}).data)

    def post(self, request, id):
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        data = {**request.data, "property": str(prop.id)}
        serializer = InspectionConfigSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save(workspace=request.workspace, property=prop)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InspectionConfigDetailView(APIView):
    """
    GET    /api/v1/properties/<id>/inspection-configs/<config_id>/  — Retrieve
    PATCH  /api/v1/properties/<id>/inspection-configs/<config_id>/  — Update
    DELETE /api/v1/properties/<id>/inspection-configs/<config_id>/  — Delete
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def _get_config(self, request, id, config_id):
        from properties.models import InspectionConfig
        try:
            return InspectionConfig.objects.get(id=config_id, property_id=id, workspace=request.workspace)
        except InspectionConfig.DoesNotExist:
            return None

    def get(self, request, id, config_id):
        from properties.serializers import InspectionConfigSerializer
        config = self._get_config(request, id, config_id)
        if config is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InspectionConfigSerializer(config, context={"request": request}).data)

    def patch(self, request, id, config_id):
        from properties.serializers import InspectionConfigSerializer
        config = self._get_config(request, id, config_id)
        if config is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = InspectionConfigSerializer(config, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, config_id):
        config = self._get_config(request, id, config_id)
        if config is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Keep the old single-config view as a compatibility shim (GET/POST → first config or create)
class InspectionConfigView(APIView):
    """
    GET  /api/v1/properties/<id>/inspection-config/  — Get first active config (legacy)
    POST /api/v1/properties/<id>/inspection-config/  — Create a config (legacy)
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    def _get_property(self, request, id):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(Property, id=id, workspace=request.workspace)

    def get(self, request, id):
        from properties.models import InspectionConfig
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        config = InspectionConfig.objects.filter(workspace=request.workspace, property=prop).order_by("-created_at").first()
        if config is None:
            return Response({}, status=status.HTTP_200_OK)
        return Response(InspectionConfigSerializer(config, context={"request": request}).data)

    def post(self, request, id):
        from properties.serializers import InspectionConfigSerializer
        prop = self._get_property(request, id)
        data = {**request.data, "property": str(prop.id)}
        serializer = InspectionConfigSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save(workspace=request.workspace, property=prop)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PropertyAvailableSlotsView(APIView):
    """
    GET /api/v1/properties/<id>/available-slots/?months=3

    Returns all available inspection slots for a property across its active
    InspectionConfigs, for the next `months` months.

    Response items:
        { date, time, label, config_id, mode, tag, slot_id }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        import uuid as _uuid
        from datetime import date, timedelta
        from dateutil.relativedelta import relativedelta
        from properties.models import InspectionConfig
        from customers.site_inspection_models import SiteInspection

        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            months = max(1, int(request.query_params.get("months", 3)))
        except (ValueError, TypeError):
            months = 3

        today = date.today()
        end_bound = today + relativedelta(months=months)

        configs = InspectionConfig.objects.filter(
            workspace=request.workspace,
            property=prop,
            is_active=True,
        )

        # Day-name → weekday index (Monday=0)
        DAY_MAP = {
            "MON": 0, "TUE": 1, "WED": 2,
            "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6,
        }

        # Count booked slots per (property, date, time) for capacity checks
        booked_counts: dict = {}
        for insp in SiteInspection.objects.filter(
            workspace=request.workspace,
            linked_property=prop,
            inspection_date__gte=today,
            inspection_date__lte=end_bound,
            status__in=["PENDING", "ATTENDED"],
        ).values("inspection_date", "inspection_time"):
            key = (str(insp["inspection_date"]), str(insp["inspection_time"]) if insp["inspection_time"] else "")
            booked_counts[key] = booked_counts.get(key, 0) + 1

        slots = []

        for config in configs:
            if config.schedule_mode == "ONE_TIME":
                if not config.inspection_date or config.inspection_date < today:
                    continue
                if config.inspection_date > end_bound:
                    continue
                t = config.inspection_time
                time_str = t.strftime("%H:%M") if t else ""
                key = (str(config.inspection_date), time_str)
                if booked_counts.get(key, 0) >= config.max_persons:
                    continue
                label = _format_slot_label(config.inspection_date, t)
                slots.append({
                    "date": str(config.inspection_date),
                    "time": time_str,
                    "label": label,
                    "config_id": str(config.id),
                    "mode": "ONE_TIME",
                    "tag": config.tag,
                    "slot_id": str(_uuid.uuid4()),
                })

            else:  # RECURRING
                available_days = config.available_days or []
                if not available_days:
                    continue

                # Determine times to generate slots for
                slot_times = []
                if config.time_slots:
                    for ts in config.time_slots:
                        if ts.get("is_active", True):
                            slot_times.append(ts.get("start_time") or ts.get("time", ""))
                elif config.time_from:
                    slot_times.append(config.time_from.strftime("%H:%M"))

                if not slot_times:
                    slot_times = [""]

                # Collect target weekday indices
                target_weekdays = set()
                for day_code in available_days:
                    idx = DAY_MAP.get(day_code.upper())
                    if idx is not None:
                        target_weekdays.add(idx)

                # Recurring end boundary
                recur_end = end_bound
                if config.end_date and config.end_date < recur_end:
                    recur_end = config.end_date

                # Walk day-by-day from tomorrow
                current = today + timedelta(days=1)
                while current <= recur_end:
                    if current.weekday() in target_weekdays:
                        for time_str in slot_times:
                            key = (str(current), time_str)
                            if booked_counts.get(key, 0) >= config.max_persons:
                                current += timedelta(days=1)
                                continue
                            # Parse time_str for label
                            t_obj = _parse_time(time_str)
                            label = _format_slot_label(current, t_obj)
                            slots.append({
                                "date": str(current),
                                "time": time_str,
                                "label": label,
                                "config_id": str(config.id),
                                "mode": "RECURRING",
                                "tag": config.tag,
                                "slot_id": str(_uuid.uuid4()),
                            })
                    current += timedelta(days=1)

        # Sort by date then time
        slots.sort(key=lambda s: (s["date"], s["time"]))
        return Response(slots)


def _parse_time(time_str):
    """Parse a HH:MM string to a time object, returning None on failure."""
    if not time_str:
        return None
    try:
        from datetime import time as dt_time
        parts = time_str.split(":")
        return dt_time(int(parts[0]), int(parts[1]))
    except Exception:
        return None


def _format_slot_label(d, t):
    """Format date + time as 'Fri, 15 May 2026, 10:00am'."""
    date_part = d.strftime("%a, %d %b %Y")
    if t:
        # Use %I (zero-padded 12h) then strip leading zero manually for cross-platform
        time_part = t.strftime("%I:%M%p").lstrip("0").lower()
        return f"{date_part}, {time_part}"
    return date_part


class PublicInspectionConfigView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/properties/<id>/inspection-config/
    Public — no auth required. Returns all active configs.
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
        configs = InspectionConfig.objects.filter(workspace=workspace, property=prop, is_active=True).order_by("-created_at")
        return Response(InspectionConfigSerializer(configs, many=True, context={"request": request}).data)


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


class AssignCustomerRepView(APIView):
    """
    PATCH /api/v1/properties/<id>/assign-customer-rep/

    Assigns a workspace member as the customer representative for a property.
    Request body: { "user_id": "<uuid>" }
    """
    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(
        tags=_PROP_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid"),
            },
        ),
        responses={200: PropertyDetailSerializer},
    )
    def patch(self, request, id):
        from accounts.models import User
        try:
            prop = Property.objects.get(id=id, workspace=request.workspace)
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id, workspace_memberships__workspace=request.workspace)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found or is not a member of this workspace."},
                status=status.HTTP_404_NOT_FOUND,
            )

        prop.assigned_customer_rep = user
        prop.save(update_fields=["assigned_customer_rep", "updated_at"])

        return Response(PropertyDetailSerializer(prop, context={"request": request}).data)


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


class PricingPlanHistoryView(generics.ListAPIView):
    """
    GET /api/v1/properties/plans/<id>/history/

    List price change history for a pricing plan.
    """

    serializer_class = PricingPlanHistorySerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def get_queryset(self):
        plan_id = self.kwargs.get("id")
        return PricingPlanHistory.objects.filter(
            workspace=self.request.workspace,
            pricing_plan_id=plan_id,
        ).select_related("changed_by").order_by("-created_at")


class PublicValidateReferralView(APIView):
    """
    GET /api/v1/public/<workspace_slug>/validate-referral/?code=<code>
    Public — no auth required. Validates a sales rep referral code.
    Returns { valid, rep_name } on success.
    """

    permission_classes = []

    def get(self, request, workspace_slug):
        from core.models import Workspace
        from commissions.models import SalesRep

        code = request.query_params.get("code", "").strip()
        if not code:
            return Response({"valid": False, "rep_name": None})

        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"valid": False, "rep_name": None})

        try:
            rep = SalesRep.objects.get(workspace=workspace, referral_code__iexact=code, is_active=True)
            return Response({"valid": True, "rep_name": rep.name})
        except SalesRep.DoesNotExist:
            return Response({"valid": False, "rep_name": None})


class PublicSiteInspectionCreateView(APIView):
    """
    POST /api/v1/public/<workspace_slug>/properties/<id>/book-inspection/
    Public — no auth required. Books a site inspection and sends confirmation email.
    """

    permission_classes = []

    def post(self, request, workspace_slug, id):
        from core.models import Workspace
        from customers.site_inspection_models import SiteInspection
        from customers.site_inspection_serializers import SiteInspectionCreateSerializer
        from customers.site_inspection_serializers import SiteInspectionSerializer
        from notifications.services import NotificationService

        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return Response({"detail": "Workspace not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            prop = Property.objects.get(id=id, workspace=workspace, status="PUBLISHED")
        except Property.DoesNotExist:
            return Response({"detail": "Property not found."}, status=status.HTTP_404_NOT_FOUND)

        data = {**request.data, "linked_property": str(prop.id), "property_name": prop.name}
        serializer = SiteInspectionCreateSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Auto-detect customer_type
        email = serializer.validated_data.get("email", "")
        customer_type = serializer.validated_data.get("customer_type", "")
        if not customer_type and email:
            from customers.models import Customer
            exists = Customer.objects.filter(workspace=workspace, email__iexact=email).exists()
            customer_type = "EXISTING" if exists else "NEW"

        inspection = serializer.save(
            workspace=workspace,
            linked_property=prop,
            property_name=prop.name,
            customer_type=customer_type,
        )

        try:
            NotificationService.send_inspection_booking_email(inspection, workspace)
        except Exception:
            pass

        return Response(
            SiteInspectionSerializer(inspection, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
