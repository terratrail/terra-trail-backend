"""
Customer self-service portal views.

Authentication flow (OTP-based, no password):
  POST /api/v1/portal/auth/request-otp/  — validate email+phone vs Customer model, send OTP
  POST /api/v1/portal/auth/verify-otp/   — verify OTP, return PortalToken

Portal endpoints (require: Authorization: PortalToken <token>):
  GET  /api/v1/portal/me/                — customer profile + active subscription overview
  GET  /api/v1/portal/subscriptions/     — list customer's subscriptions
  GET  /api/v1/portal/subscriptions/<id>/— subscription detail with installments + payment history
  POST /api/v1/portal/payments/          — record a payment (receipt upload is mandatory)

PRD requirements enforced:
  - Email AND phone must both match a single Customer record
  - OTP lockout after 3 failed attempts (handled by OTPService)
  - Session expires after 30 minutes (CustomerPortalSession.SESSION_MINUTES)
  - Customer can only see their own data
  - Receipt upload is mandatory for customer-submitted payments
  - Customer cannot submit a second payment for an installment that is already PENDING
"""

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import CustomerPortalAuthentication, IsCustomerPortalUser
from accounts.services import OTPService
from accounts.throttles import OTPRequestThrottle, OTPVerifyThrottle
from customers.models import Customer, CustomerPortalSession, Installment, Subscription
from customers.serializers import InstallmentSerializer, SubscriptionSerializer
from payments.models import Payment
from payments.serializers import PaymentSerializer, RecordPaymentSerializer
from payments.services import PaymentService

logger = logging.getLogger("terratrail")

_PORTAL_TAG = ["Customer Portal"]


# ---------------------------------------------------------------------------
# Auth — OTP request and verify
# ---------------------------------------------------------------------------

class PortalOTPRequestView(APIView):
    """
    POST /api/v1/portal/auth/request-otp/

    Step 1 of portal login. Validates that a customer with the given
    email AND phone exists, then sends a 6-digit OTP to their email.
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestThrottle]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "phone"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response("OTP sent to customer's email."),
            404: openapi.Response("No matching customer found."),
            429: openapi.Response("Rate limited / locked out."),
        },
        operation_description=(
            "Request a portal OTP. Both email AND phone must match a single customer "
            "record. OTP is sent to the customer's email address."
        ),
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        phone = request.data.get("phone", "").strip()

        if not email or not phone:
            return Response(
                {"message": "Both email and phone are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Both must match a single customer (PRD 5.6.1)
        try:
            Customer.objects.get(email=email, phone=phone)
        except Customer.DoesNotExist:
            return Response(
                {"message": "No account found. Please contact your estate manager."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Customer.MultipleObjectsReturned:
            # Unlikely but handle gracefully
            return Response(
                {"message": "Multiple accounts found. Please contact your estate manager."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            code = OTPService.request_otp(email=email, phone=phone)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        response_data = {"message": "OTP sent to your email address."}

        # Return code in DEBUG mode for testing
        from django.conf import settings
        if settings.DEBUG:
            response_data["code"] = code

        logger.info(f"Portal OTP requested for customer: {email}")
        return Response(response_data)


class PortalOTPVerifyView(APIView):
    """
    POST /api/v1/portal/auth/verify-otp/

    Step 2 of portal login. Verifies the OTP and returns a portal session token.
    The token must be sent as: Authorization: PortalToken <token>
    """

    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "phone", "code"],
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                "phone": openapi.Schema(type=openapi.TYPE_STRING),
                "code": openapi.Schema(type=openapi.TYPE_STRING, description="6-digit OTP"),
            },
        ),
        responses={
            200: openapi.Response("Portal session token."),
            400: openapi.Response("Invalid / expired OTP."),
        },
        operation_description="Verify OTP and receive a 30-minute portal session token.",
    )
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        phone = request.data.get("phone", "").strip()
        code  = request.data.get("code", "").strip()

        if not email or not phone or not code:
            return Response(
                {"message": "email, phone, and code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify OTP (handles lockout, expiry, attempt tracking)
        try:
            OTPService.verify_otp_for_portal(email=email, phone=phone, code=code)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the customer
        try:
            customer = Customer.objects.get(email=email, phone=phone)
        except Customer.DoesNotExist:
            return Response(
                {"message": "Customer record not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Invalidate any existing active sessions for this customer
        CustomerPortalSession.objects.filter(customer=customer, is_active=True).update(
            is_active=False
        )

        # Create a new 30-minute session
        session = CustomerPortalSession.create_for_customer(customer)

        logger.info(f"Portal session created for customer: {email}")
        return Response({
            "message": "Login successful.",
            "token": session.token,
            "expires_at": session.expires_at.isoformat(),
            "customer": {
                "id": str(customer.id),
                "full_name": customer.full_name,
                "email": customer.email,
                "phone": customer.phone,
            },
        })


# ---------------------------------------------------------------------------
# Portal data endpoints
# ---------------------------------------------------------------------------

class PortalMeView(APIView):
    """
    GET /api/v1/portal/me/

    Returns the authenticated customer's profile and a summary of all
    their active subscriptions.
    """

    authentication_classes = [CustomerPortalAuthentication]
    permission_classes = [IsCustomerPortalUser]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        operation_description="Get the authenticated customer's profile and subscription summary.",
    )
    def get(self, request):
        customer = request.user.customer

        subscriptions = (
            Subscription.objects.filter(customer=customer)
            .select_related("property", "pricing_plan")
            .order_by("-created_at")
        )

        sub_summaries = []
        for sub in subscriptions:
            next_installment = (
                sub.installments
                .filter(status__in=[Installment.Status.DUE, Installment.Status.OVERDUE])
                .order_by("due_date")
                .first()
            )
            sub_summaries.append({
                "id": str(sub.id),
                "property_name": sub.property.name,
                "plan_name": sub.pricing_plan.plan_name,
                "total_price": str(sub.total_price),
                "amount_paid": str(sub.amount_paid),
                "balance": str(sub.balance),
                "status": sub.status,
                "next_due_date": next_installment.due_date.isoformat() if next_installment else None,
                "next_due_amount": str(next_installment.amount) if next_installment else None,
            })

        return Response({
            "id": str(customer.id),
            "full_name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone,
            "address": customer.address,
            "subscriptions": sub_summaries,
        })


class PortalSubscriptionListView(APIView):
    """
    GET /api/v1/portal/subscriptions/

    List all subscriptions for the authenticated customer.
    """

    authentication_classes = [CustomerPortalAuthentication]
    permission_classes = [IsCustomerPortalUser]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        operation_description="List all subscriptions for the authenticated customer.",
    )
    def get(self, request):
        customer = request.user.customer
        subscriptions = (
            Subscription.objects.filter(customer=customer)
            .select_related("property", "pricing_plan")
            .prefetch_related("installments")
            .order_by("-created_at")
        )
        return Response(SubscriptionSerializer(subscriptions, many=True).data)


class PortalSubscriptionDetailView(APIView):
    """
    GET /api/v1/portal/subscriptions/<id>/

    Full subscription detail — installments + approved payment history.
    Customers can only access their own subscriptions.
    """

    authentication_classes = [CustomerPortalAuthentication]
    permission_classes = [IsCustomerPortalUser]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        operation_description="Get full subscription detail including installments and payment history.",
    )
    def get(self, request, id):
        customer = request.user.customer
        try:
            subscription = (
                Subscription.objects.select_related("property", "pricing_plan")
                .prefetch_related("installments")
                .get(id=id, customer=customer)
            )
        except Subscription.DoesNotExist:
            return Response(
                {"message": "Subscription not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Payment history (approved only, for display)
        payments = (
            Payment.objects.filter(
                installment__subscription=subscription,
                status=Payment.Status.APPROVED,
            )
            .select_related("recorded_by")
            .order_by("-created_at")
        )

        bank_accounts = list(
            subscription.property.bank_accounts.filter(is_active=True)
            .values("id", "bank_name", "account_name", "account_number")
        )

        return Response({
            "subscription": SubscriptionSerializer(subscription).data,
            "payment_history": PaymentSerializer(payments, many=True).data,
            "bank_accounts": bank_accounts,
        })


class PortalRecordPaymentView(APIView):
    """
    POST /api/v1/portal/payments/

    Customer records a payment against one of their Due or Overdue installments.

    PRD rules enforced:
    - Receipt file upload is mandatory
    - Installment must belong to the authenticated customer
    - Installment must be DUE or OVERDUE
    - Cannot submit a second payment if one is already PENDING
    """

    authentication_classes = [CustomerPortalAuthentication]
    permission_classes = [IsCustomerPortalUser]

    @swagger_auto_schema(
        tags=_PORTAL_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["installment_id", "amount", "receipt_file"],
            properties={
                "installment_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "receipt_file": openapi.Schema(type=openapi.TYPE_STRING, description="File upload (multipart/form-data)"),
                "notes": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            201: PaymentSerializer,
            400: openapi.Response("Validation error or business rule violation."),
            404: openapi.Response("Installment not found or not accessible."),
        },
        operation_description=(
            "Record a payment against a Due or Overdue installment. "
            "Receipt file upload is mandatory. Content-Type must be multipart/form-data."
        ),
    )
    def post(self, request):
        customer = request.user.customer

        installment_id = request.data.get("installment_id")
        amount         = request.data.get("amount")
        receipt_file   = request.FILES.get("receipt_file")
        notes          = request.data.get("notes", "")

        # Validate required fields
        if not installment_id:
            return Response({"message": "installment_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not amount:
            return Response({"message": "amount is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not receipt_file:
            return Response(
                {"message": "receipt_file is required for customer-submitted payments."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch installment and verify ownership
        try:
            installment = Installment.objects.select_related("subscription__customer").get(
                id=installment_id,
                subscription__customer=customer,
            )
        except Installment.DoesNotExist:
            return Response(
                {"message": "Installment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Only DUE or OVERDUE installments can accept a payment
        if installment.status not in [Installment.Status.DUE, Installment.Status.OVERDUE]:
            return Response(
                {"message": f"Cannot record a payment for an installment with status '{installment.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Workspace is derived from the subscription
        workspace = installment.subscription.workspace

        try:
            payment = PaymentService.record_payment(
                workspace=workspace,
                installment=installment,
                amount=amount,
                recorded_by=None,  # Customer portal — no admin user
                receipt_file=receipt_file,
                notes=notes,
            )
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            f"Portal payment recorded: installment {installment.id} "
            f"by customer {customer.email}"
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)
