"""
Accounts throttles — Rate limiting for sensitive auth endpoints.
"""

from rest_framework.throttling import AnonRateThrottle


class OTPRequestThrottle(AnonRateThrottle):
    """
    Limits OTP request attempts per IP.

    Prevents mass SMS/email triggering from a single address.
    Rate is configured via DEFAULT_THROTTLE_RATES["otp_request"] in settings.
    """
    scope = "otp_request"


class OTPVerifyThrottle(AnonRateThrottle):
    """
    Limits OTP verification attempts per IP.

    Adds a network-level rate limit on top of the per-token lockout
    already implemented in OTPService.
    Rate is configured via DEFAULT_THROTTLE_RATES["otp_verify"] in settings.
    """
    scope = "otp_verify"
