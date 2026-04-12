"""
TerraTrail — Root URL Configuration.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from django.contrib import admin

admin.site.site_header = (
    "TerraTrail Management"  # Appears at the top of the admin pages
)
admin.site.site_title = "TerraTrail Management"  # Appears in the browser tab title
admin.site.index_title = (
    "Welcome to TerraTrail Admin Portal"  # Appears on the main admin page
)


schema_view = get_schema_view(
    openapi.Info(
        title="TerraTrail API",
        default_version="v1",
        description="TerraTrail API Documentation",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="[EMAIL_ADDRESS]"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

from core.views import WorkspaceHomeView

urlpatterns = [
    path("", WorkspaceHomeView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/workspaces/", include("core.urls")),
    path("api/v1/properties/", include("properties.urls")),
    path("api/v1/customers/", include("customers.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/commissions/", include("commissions.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path(
        "api/v1/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/v1/redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
