"""
TerraTrail SaaS plan definitions.

PLAN_LIMITS defines hard resource caps per plan.
None = unlimited.

Workspace limit: how many workspaces the plan owner can create/own.
Per-workspace limits: properties and customers are scoped per workspace.
Sales reps and team members are unlimited on all paid plans.

PLAN_CATALOGUE is the public-facing description served to the onboarding UI
via GET /api/v1/workspaces/billing/plans/.
"""

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
            "1 sales rep",
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
# Payment details (bank transfer)
# ---------------------------------------------------------------------------

PAYMENT_DETAILS = {
    "bank_name": "Guaranty Trust Bank",
    "account_name": "TerraTrail Technologies Ltd",
    "account_number": "0123456789",   # TODO: replace with real account
    "currency": "NGN",
    "instructions": (
        "Transfer the plan amount to the account above. "
        "Use your registered email as the payment reference. "
        "Send your proof of payment to billing@terratrail.io "
        "and your plan will be activated within 24 hours."
    ),
}


def get_plan_limits(billing_plan: str) -> dict:
    """Return the resource limits for a given billing plan key."""
    return PLAN_LIMITS.get(billing_plan, PLAN_LIMITS["FREE"])
