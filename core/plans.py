"""
TerraTrail SaaS plan definitions.

PLAN_LIMITS defines hard resource caps per plan.
None = unlimited.

Workspace limit: how many workspaces the plan owner can create/own.
Per-workspace limits: properties and customers are scoped per workspace.
Sales reps and team members are unlimited on all plans.

PLAN_CATALOGUE is the public-facing description served to the onboarding UI
via GET /api/v1/workspaces/billing/plans/.

Payment details are loaded from environment variables via terratrail.config
so they are never hardcoded in source code.
"""

from terratrail.config import settings as app_settings


# ---------------------------------------------------------------------------
# Resource limits per plan
# ---------------------------------------------------------------------------

PLAN_LIMITS = {
    "FREE": {
        "workspaces": 1,
        "properties": 1,
        "customers": 2,
        "sales_reps": None,
        "team_members": 1,
    },
    "STARTER": {
        "workspaces": 1,
        "properties": 5,
        "customers": 500,
        "sales_reps": None,
        "team_members": None,
    },
    "GROWTH": {
        "workspaces": 2,
        "properties": 10,
        "customers": 2000,
        "sales_reps": None,
        "team_members": None,
    },
    "SCALE": {
        "workspaces": 3,
        "properties": 30,
        "customers": 5000,
        "sales_reps": None,
        "team_members": None,
    },
    "ENTERPRISE": {
        "workspaces": None,
        "properties": None,
        "customers": None,
        "sales_reps": None,
        "team_members": None,
    },
}


# ---------------------------------------------------------------------------
# Public-facing plan catalogue
# ---------------------------------------------------------------------------

PLAN_CATALOGUE = [
    {
        "key": "FREE",
        "name": "Free",
        "price_monthly": 0,
        "price_yearly": 0,
        "yearly_savings_percent": 0,
        "currency": "NGN",
        "contact_sales": False,
        "description": "Get started at no cost. One estate, two customers.",
        "limits": PLAN_LIMITS["FREE"],
        "features": [
            "1 workspace",
            "1 estate",
            "2 customers",
            "Unlimited sales reps",
            "Basic payment & installment tracking",
        ],
        "recommended": False,
    },
    {
        "key": "STARTER",
        "name": "Starter",
        "price_monthly": 50_000,
        "price_yearly": 500_000,
        "yearly_savings_percent": 16.67,
        "currency": "NGN",
        "contact_sales": False,
        "description": "For growing agencies managing multiple properties.",
        "limits": PLAN_LIMITS["STARTER"],
        "features": [
            "1 workspace",
            "5 estates",
            "500 customers",
            "Unlimited sales reps",
            "Unlimited team members",
            "Email & SMS notifications",
            "Activity audit logs",
            "Commission tracking",
        ],
        "recommended": False,
    },
    {
        "key": "GROWTH",
        "name": "Growth",
        "price_monthly": 100_000,
        "price_yearly": 1_000_000,
        "yearly_savings_percent": 16.67,
        "currency": "NGN",
        "contact_sales": False,
        "description": "For established companies scaling across multiple offices.",
        "limits": PLAN_LIMITS["GROWTH"],
        "features": [
            "2 workspaces",
            "10 estates per workspace",
            "2,000 customers per workspace",
            "Unlimited sales reps",
            "Unlimited team members",
            "All Starter features",
            "Priority support",
        ],
        "recommended": True,
    },
    {
        "key": "SCALE",
        "name": "Scale",
        "price_monthly": 200_000,
        "price_yearly": 2_000_000,
        "yearly_savings_percent": 16.67,
        "currency": "NGN",
        "contact_sales": False,
        "description": "For large operations running multiple regional offices.",
        "limits": PLAN_LIMITS["SCALE"],
        "features": [
            "3 workspaces",
            "30 estates per workspace",
            "5,000 customers per workspace",
            "Unlimited sales reps",
            "Unlimited team members",
            "All Growth features",
        ],
        "recommended": False,
    },
    {
        "key": "ENTERPRISE",
        "name": "Enterprise",
        "price_monthly": None,
        "price_yearly": None,
        "yearly_savings_percent": None,
        "currency": "NGN",
        "contact_sales": True,
        "description": "Custom SLA, integrations, and unlimited scale. Contact our sales team.",
        "limits": PLAN_LIMITS["ENTERPRISE"],
        "features": [
            "Unlimited workspaces",
            "Unlimited estates",
            "Unlimited customers",
            "Unlimited sales reps & team members",
            "All Scale features",
            "Dedicated account manager",
            "Custom SLA",
            "Custom integrations",
        ],
        "recommended": False,
    },
]


# ---------------------------------------------------------------------------
# Payment details — loaded from environment via config
# ---------------------------------------------------------------------------

PAYMENT_DETAILS = {
    "bank_name": app_settings.BANK_NAME,
    "account_name": app_settings.BANK_ACCOUNT_NAME,
    "account_number": app_settings.BANK_ACCOUNT_NUMBER,
    "currency": app_settings.PAYMENT_CURRENCY,
    "instructions": app_settings.PAYMENT_INSTRUCTIONS,
}


def get_plan_limits(billing_plan: str) -> dict:
    """Return the resource limits for a given billing plan key."""
    return PLAN_LIMITS.get(billing_plan, PLAN_LIMITS["FREE"])
