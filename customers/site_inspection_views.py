"""
SiteInspection views.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from core.permissions import IsWorkspaceMember
from customers.site_inspection_models import SiteInspection
from customers.site_inspection_serializers import (
    SiteInspectionCreateSerializer,
    SiteInspectionSerializer,
)

_TAG = ["Site Inspections"]


class SiteInspectionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/customers/site-inspections/   — List all inspection requests
    POST /api/v1/customers/site-inspections/   — Create an inspection request
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SiteInspectionCreateSerializer
        return SiteInspectionSerializer

    def get_queryset(self):
        qs = SiteInspection.objects.filter(workspace=self.request.workspace)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    @swagger_auto_schema(tags=_TAG)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=_TAG,
        request_body=SiteInspectionCreateSerializer,
        responses={201: SiteInspectionSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(workspace=self.request.workspace)


class SiteInspectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/customers/site-inspections/<id>/  — Retrieve
    PATCH  /api/v1/customers/site-inspections/<id>/  — Update (e.g. mark attended)
    DELETE /api/v1/customers/site-inspections/<id>/  — Delete
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember]
    serializer_class = SiteInspectionSerializer
    lookup_field = "id"
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return SiteInspection.objects.filter(workspace=self.request.workspace)

    @swagger_auto_schema(tags=_TAG)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @swagger_auto_schema(tags=_TAG)
    def patch(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=_TAG)
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
