"""
TerraTrail — Root URL Configuration.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/workspaces/", include("core.urls")),
    path("api/v1/properties/", include("properties.urls")),
    path("api/v1/customers/", include("customers.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/commissions/", include("commissions.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
