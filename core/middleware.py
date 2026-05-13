"""
Workspace middleware — Extracts workspace from the request.

Supports two resolution strategies:
1. X-Workspace header (slug)
2. Subdomain extraction (e.g., acme.terratrail.io)

Public endpoints (auth, docs) skip workspace resolution.
"""

import re
from django.http import JsonResponse
from core.models import Workspace

# URL patterns that do NOT require workspace context
PUBLIC_PATHS = [
    r"^/admin/",
    r"^/admin",
    r"^/api/v1/auth/",
    r"^/api/v1/workspaces/create/?$",
    r"^/api/v1/workspaces/mine/?$",
    r"^/api/v1/workspaces/check-slug/?",
    r"^/api/v1/docs/",
    r"^/api/v1/redoc/",
    r"^/api/v1/health/",
    r"^/docs.json/",
    r"^/swagger",
    r"^/static/",
    r"^/media/",
    r"^/$",
    r"^/api/v1/workspaces/invites/[^/]+/?$",  # GET invite detail — public preview
    r"^/api/v1/workspaces/invites/[^/]+/accept/?$",  # POST accept — workspace from token, not header
    r"^/api/v1/public/",  # Public estate listing — no workspace header needed
    r"^/api/v1/properties/bulk-upload/template/",
    r"^/api/v1/customers/bulk-upload/template/",
]


class WorkspaceMiddleware:
    """
    Injects `request.workspace` for all workspace-scoped endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.public_patterns = [re.compile(p) for p in PUBLIC_PATHS]

    def __call__(self, request):
        request.workspace = None

        # Skip workspace resolution for public paths
        if self._is_public(request.path):
            return self.get_response(request)

        # Strategy 1: Header — accept both X-Workspace-Slug and X-Workspace
        workspace_slug = (
            request.headers.get("X-Workspace-Slug", "").strip()
            or request.headers.get("X-Workspace", "").strip()
        )

        # Strategy 2: Subdomain fallback
        if not workspace_slug:
            workspace_slug = self._extract_subdomain(request)

        if not workspace_slug:
            return JsonResponse(
                {
                    "message": "Workspace context required. Provide X-Workspace-Slug header."
                },
                status=400,
            )

        try:
            workspace = Workspace.objects.get(slug=workspace_slug, is_active=True)
        except Workspace.DoesNotExist:
            return JsonResponse(
                {"message": f"Workspace '{workspace_slug}' not found or inactive."},
                status=404,
            )

        request.workspace = workspace
        return self.get_response(request)

    def _is_public(self, path):
        return any(pattern.match(path) for pattern in self.public_patterns)

    def _extract_subdomain(self, request):
        """Extract workspace slug from subdomain."""
        host = request.get_host().split(":")[0].lower()
        parts = host.split(".")

        # Handle acme.localhost
        if len(parts) == 2 and parts[1] == "localhost":
            return parts[0]

        # Handle acme.terratrail.io
        if len(parts) >= 3:
            return parts[0]

        return None
