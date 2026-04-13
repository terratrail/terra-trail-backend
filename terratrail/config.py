"""
TerraTrail application configuration.

All SaaS-level constants — company identity, payment details, URLs — are
loaded from environment variables here. Other modules import from this file
instead of hardcoding values directly.

Usage:
    from terratrail.config import settings as app_settings

    subject = f"Welcome to {app_settings.COMPANY_NAME}"
    payment_info = app_settings.BANK_ACCOUNT_NUMBER
"""

from decouple import config as env


class Settings:
    """
    Application-level SaaS configuration for TerraTrail.
    All values are loaded from environment variables with sensible defaults.
    """

    # -------------------------------------------------------------------------
    # Company Identity
    # -------------------------------------------------------------------------
    COMPANY_NAME: str = env("COMPANY_NAME", default="TerraTrail Technologies Ltd")
    SUPPORT_EMAIL: str = env("SUPPORT_EMAIL", default="support@terratrail.io")
    SALES_EMAIL: str = env("SALES_EMAIL", default="sales@terratrail.io")
    BILLING_EMAIL: str = env("BILLING_EMAIL", default="billing@terratrail.io")

    # -------------------------------------------------------------------------
    # URLs
    # -------------------------------------------------------------------------
    FRONTEND_BASE_URL: str = env("FRONTEND_BASE_URL", default="http://localhost:3000")
    BACKEND_BASE_URL: str = env("BACKEND_BASE_URL", default="http://localhost:8000")

    # -------------------------------------------------------------------------
    # Bank / Payment Details
    # Used in the plan-upgrade bank-transfer flow (GET /billing/plans/).
    # -------------------------------------------------------------------------
    BANK_NAME: str = env("BANK_NAME", default="Guaranty Trust Bank")
    BANK_ACCOUNT_NAME: str = env(
        "BANK_ACCOUNT_NAME", default="TerraTrail Technologies Ltd"
    )
    BANK_ACCOUNT_NUMBER: str = env("BANK_ACCOUNT_NUMBER", default="")
    PAYMENT_CURRENCY: str = env("PAYMENT_CURRENCY", default="NGN")
    PAYMENT_INSTRUCTIONS: str = env(
        "PAYMENT_INSTRUCTIONS",
        default=(
            "Transfer the plan amount to the account above. "
            "Use your registered email as the payment reference. "
            "Send your proof of payment to billing@terratrail.io "
            "and your plan will be activated within 24 hours."
        ),
    )


settings = Settings()
