"""
Core utilities — Shared helpers.
"""

import random
import string
from decimal import Decimal, ROUND_HALF_UP


def generate_otp(length=6):
    """Generate a numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))


def generate_reference(prefix="TT"):
    """Generate a unique transaction reference."""
    import shortuuid
    return f"{prefix}-{shortuuid.uuid()[:12].upper()}"


def round_currency(amount):
    """Round a decimal amount to 2 decimal places (standard currency rounding)."""
    return Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
