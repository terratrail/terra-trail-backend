"""
PlanGuard — Enforces per-plan resource limits.

Workspace-level limits (properties, customers, sales_reps, team_members)
are scoped per workspace and checked against that workspace's billing_plan.

The workspace count limit is user-scoped: it checks how many workspaces
the requesting user already OWNS, against their primary workspace's plan.

Usage:
    from core.plan_guard import PlanGuard, PlanLimitExceeded

    try:
        PlanGuard.check_workspace_limit(request.user)
        PlanGuard.check_property_limit(request.workspace)
    except PlanLimitExceeded as e:
        return Response({"message": str(e)}, status=402)
"""

from core.plans import get_plan_limits


class PlanLimitExceeded(Exception):
    """Raised when a workspace or user has reached their plan's resource cap."""
    pass


class PlanGuard:

    # Roles that are unlimited on every plan — never count against the cap
    _UNLIMITED_ROLES = {"SALES_REP", "CUSTOMER"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _limit(workspace, resource):
        return get_plan_limits(workspace.billing_plan).get(resource)

    @staticmethod
    def _user_plan(user):
        """
        Resolve the billing plan for a user.

        A user's effective plan is determined by their primary workspace —
        the earliest workspace where they hold the OWNER role.
        Falls back to FREE if they own no workspace yet.
        """
        from accounts.models import WorkspaceMembership
        primary = (
            WorkspaceMembership.objects.filter(
                user=user,
                role=WorkspaceMembership.Role.OWNER,
                is_active=True,
            )
            .order_by("created_at")
            .select_related("workspace")
            .first()
        )
        return primary.workspace.billing_plan if primary else "FREE"

    # ------------------------------------------------------------------
    # Workspace-count limit (user-scoped)
    # ------------------------------------------------------------------

    @staticmethod
    def check_workspace_limit(user):
        """
        Check whether the user is allowed to create another workspace
        based on their current plan.
        """
        from accounts.models import WorkspaceMembership
        plan = PlanGuard._user_plan(user)
        limit = get_plan_limits(plan).get("workspaces")
        if limit is None:
            return
        owned = WorkspaceMembership.objects.filter(
            user=user,
            role=WorkspaceMembership.Role.OWNER,
            is_active=True,
        ).count()
        if owned >= limit:
            noun = "workspace" if limit == 1 else "workspaces"
            raise PlanLimitExceeded(
                f"Your {plan} plan allows up to {limit} {noun}. "
                f"Upgrade your plan to create more."
            )

    # ------------------------------------------------------------------
    # Per-workspace resource limits
    # ------------------------------------------------------------------

    @staticmethod
    def check_property_limit(workspace):
        limit = PlanGuard._limit(workspace, "properties")
        if limit is None:
            return
        from properties.models import Property
        count = Property.objects.filter(workspace=workspace).count()
        if count >= limit:
            noun = "estate" if limit == 1 else "estates"
            raise PlanLimitExceeded(
                f"Your {workspace.billing_plan} plan allows up to {limit} {noun}. "
                f"Upgrade your plan to add more."
            )

    @staticmethod
    def check_customer_limit(workspace):
        limit = PlanGuard._limit(workspace, "customers")
        if limit is None:
            return
        from customers.models import Customer
        count = Customer.objects.filter(workspace=workspace).count()
        if count >= limit:
            noun = "customer" if limit == 1 else "customers"
            raise PlanLimitExceeded(
                f"Your {workspace.billing_plan} plan allows up to {limit} {noun}. "
                f"Upgrade your plan to add more."
            )

    @staticmethod
    def check_sales_rep_limit(workspace):
        limit = PlanGuard._limit(workspace, "sales_reps")
        if limit is None:
            return
        from commissions.models import SalesRep
        count = SalesRep.objects.filter(workspace=workspace, is_active=True).count()
        if count >= limit:
            noun = "sales rep" if limit == 1 else "sales reps"
            raise PlanLimitExceeded(
                f"Your {workspace.billing_plan} plan allows up to {limit} {noun}. "
                f"Upgrade your plan to add more."
            )

    @staticmethod
    def check_team_member_limit(workspace, role=None):
        # SALES_REP and CUSTOMER roles are unlimited on all plans
        if role and role.upper() in PlanGuard._UNLIMITED_ROLES:
            return

        limit = PlanGuard._limit(workspace, "team_members")
        if limit is None:
            return
        from accounts.models import WorkspaceMembership
        # Exclude the workspace owner and unlimited roles — they don't consume slots
        count = WorkspaceMembership.objects.filter(
            workspace=workspace, is_active=True,
        ).exclude(role=WorkspaceMembership.Role.OWNER).exclude(
            role__in=PlanGuard._UNLIMITED_ROLES,
        ).count()
        if count >= limit:
            noun = "team member" if limit == 1 else "team members"
            raise PlanLimitExceeded(
                f"Your {workspace.billing_plan} plan allows up to {limit} {noun}. "
                f"Upgrade your plan to add more."
            )

    # ------------------------------------------------------------------
    # Usage snapshot (for billing/usage/ endpoint)
    # ------------------------------------------------------------------

    @staticmethod
    def get_usage(user, workspace):
        """
        Return current usage counts and limits for the workspace,
        plus workspace count for the user.
        """
        from properties.models import Property
        from customers.models import Customer
        from commissions.models import SalesRep
        from accounts.models import WorkspaceMembership

        ws_limits = get_plan_limits(workspace.billing_plan)
        user_plan = PlanGuard._user_plan(user)
        user_limits = get_plan_limits(user_plan)

        owned_workspaces = WorkspaceMembership.objects.filter(
            user=user,
            role=WorkspaceMembership.Role.OWNER,
            is_active=True,
        ).count()

        return {
            "plan": workspace.billing_plan,
            "resources": {
                "workspaces": {
                    "used": owned_workspaces,
                    "limit": user_limits["workspaces"],
                },
                "properties": {
                    "used": Property.objects.filter(workspace=workspace).count(),
                    "limit": ws_limits["properties"],
                },
                "customers": {
                    "used": Customer.objects.filter(workspace=workspace).count(),
                    "limit": ws_limits["customers"],
                },
                "sales_reps": {
                    "used": SalesRep.objects.filter(
                        workspace=workspace, is_active=True
                    ).count(),
                    "limit": ws_limits["sales_reps"],
                },
                "team_members": {
                    "used": WorkspaceMembership.objects.filter(
                        workspace=workspace, is_active=True,
                    ).exclude(role=WorkspaceMembership.Role.OWNER).exclude(
                        role__in=PlanGuard._UNLIMITED_ROLES,
                    ).count(),
                    "limit": ws_limits["team_members"],
                },
            },
        }
