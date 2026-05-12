"""
TerraTrail SaaS plan definitions.

PLAN_LIMITS defines hard resource caps per plan.
None = unlimited.

Billing cycle: quarterly (3 months).

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
        "sales_reps": 1,
        "team_members": 1,
    },
    "STARTER": {
        "workspaces": 1,
        "properties": 3,
        "customers": 500,
        "sales_reps": None,
        "team_members": 10,
    },
    "GROWTH": {
        "workspaces": 1,
        "properties": 10,
        "customers": 2000,
        "sales_reps": None,
        "team_members": None,
    },
    "SCALE": {
        "workspaces": 3,
        "properties": 20,
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
        "price_quarterly": 0,
        "currency": "NGN",
        "billing_period": "quarterly",
        "contact_sales": False,
        "description": "Get started at no cost. One estate, two customers.",
        "limits": PLAN_LIMITS["FREE"],
        "features": [
            "1 workspace",
            "1 property",
            "2 customers",
            "1 sales rep",
            "1 customer rep",
            "Basic payment & installment tracking",
        ],
        "recommended": False,
    },
    {
        "key": "STARTER",
        "name": "Starter",
        "price_quarterly": 300_000,
        "currency": "NGN",
        "billing_period": "quarterly",
        "contact_sales": False,
        "description": "For growing agencies managing multiple properties.",
        "limits": PLAN_LIMITS["STARTER"],
        "features": [
            "1 workspace",
            "3 properties",
            "500 customers",
            "Unlimited sales reps",
            "10 team members",
            "Email & SMS notifications",
            "Activity audit logs",
            "Commission tracking",
        ],
        "recommended": False,
    },
    {
        "key": "GROWTH",
        "name": "Growth",
        "price_quarterly": 450_000,
        "currency": "NGN",
        "billing_period": "quarterly",
        "contact_sales": False,
        "description": "For established companies scaling across multiple offices.",
        "limits": PLAN_LIMITS["GROWTH"],
        "features": [
            "1 workspace",
            "10 properties",
            "2,000 customers",
            "Unlimited sales reps",
            "Unlimited team members",
            "Email notifications",
            "Activity audit logs",
            "Commission tracking",
            "Priority support",
        ],
        "recommended": True,
    },
    {
        "key": "SCALE",
        "name": "Scale",
        "price_quarterly": 750_000,
        "currency": "NGN",
        "billing_period": "quarterly",
        "contact_sales": False,
        "description": "For large operations running multiple regional offices.",
        "limits": PLAN_LIMITS["SCALE"],
        "features": [
            "3 workspaces",
            "20 properties per workspace",
            "5,000 customers per workspace",
            "Unlimited sales reps",
            "Unlimited team members",
            "All Growth features",
            "Priority support",
        ],
        "recommended": False,
    },
    {
        "key": "ENTERPRISE",
        "name": "Enterprise",
        "price_quarterly": None,
        "currency": "NGN",
        "billing_period": "quarterly",
        "contact_sales": True,
        "description": "Custom SLA, integrations, and unlimited scale. Contact our sales team.",
        "limits": PLAN_LIMITS["ENTERPRISE"],
        "features": [
            "Unlimited workspaces",
            "Unlimited properties",
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
