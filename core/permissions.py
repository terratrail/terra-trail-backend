"""
Core permissions — Role-based access control and customer portal auth.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission


# ---------------------------------------------------------------------------
# Customer portal authentication
# ---------------------------------------------------------------------------

class PortalUser:
    """
    Lightweight proxy returned by CustomerPortalAuthentication.

    DRF requires request.user to have `is_authenticated`. This wraps a
    Customer instance so portal views can do `request.user.customer`.
    """

    is_authenticated = True
    is_anonymous = False

    def __init__(self, customer):
        self.customer = customer
        self.pk = customer.pk
        self.id = customer.id


class CustomerPortalAuthentication(BaseAuthentication):
    """
    DRF authentication backend for the customer self-service portal.

    Reads the token from:
        Authorization: PortalToken <token>

    On success sets:
        request.user  = PortalUser(customer)
        request.auth  = CustomerPortalSession instance
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("PortalToken "):
            return None

        token_key = auth_header.split(" ", 1)[1].strip()

        from customers.models import CustomerPortalSession

        try:
            session = CustomerPortalSession.objects.select_related("customer").get(
                token=token_key,
                is_active=True,
            )
        except CustomerPortalSession.DoesNotExist:
            raise AuthenticationFailed("Invalid portal token.")

        if session.is_expired:
            session.is_active = False
            session.save(update_fields=["is_active", "updated_at"])
            raise AuthenticationFailed("Portal session has expired. Please log in again.")

        return (PortalUser(session.customer), session)

    def authenticate_header(self, _request):
        return "PortalToken"


class IsCustomerPortalUser(BasePermission):
    """Allows access only to authenticated customer portal users."""

    def has_permission(self, request, view):
        return isinstance(request.user, PortalUser)


class IsWorkspaceMember(BasePermission):
    """Allows access only to members of the current workspace."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace, is_active=True
        ).exists()


class IsWorkspaceOwner(BasePermission):
    """Allows access only to workspace owners."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace, role="OWNER", is_active=True
        ).exists()


class IsWorkspaceAdmin(BasePermission):
    """Allows access to workspace owners and admins."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role__in=["OWNER", "ADMIN"],
            is_active=True,
        ).exists()


class IsWorkspaceAdminOrReadOnly(BasePermission):
    """Admin/Owner can write; members can read."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return request.user.workspace_memberships.filter(
                workspace=request.workspace, is_active=True
            ).exists()

        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role__in=["OWNER", "ADMIN"],
            is_active=True,
        ).exists()


class IsSalesRep(BasePermission):
    """Allows access to sales representatives."""

    def has_permission(self, request, view):
        if not request.workspace or not request.user.is_authenticated:
            return False
        return request.user.workspace_memberships.filter(
            workspace=request.workspace,
            role="SALES_REP",
            is_active=True,
        ).exists()
