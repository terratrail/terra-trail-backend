"""
Public (unauthenticated) property URL routes.
Mounted at /api/v1/public/ in the root URL config.
"""

from django.urls import path
from properties.views import PublicPropertyListView, PublicPropertyDetailView

urlpatterns = [
    path("<slug:workspace_slug>/properties/", PublicPropertyListView.as_view(), name="public-property-list"),
    path("<slug:workspace_slug>/properties/<uuid:id>/", PublicPropertyDetailView.as_view(), name="public-property-detail"),
]
