"""
Payments views — Record, approve, reject payments.
"""

from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

_PAY_TAG = ["Payments"]

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from customers.models import Installment
from payments.models import Payment
from payments.serializers import (
    ApproveRejectSerializer,
    PaymentSerializer,
    RecordPaymentSerializer,
)
from payments.services import PaymentService


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_PAY_TAG))
class PaymentListView(generics.ListAPIView):
    """
    GET /api/v1/payments/

    List all payments in the workspace, filterable by status.
    """

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    filterset_fields = ["status"]

    def get_queryset(self):
        return (
            Payment.objects.filter(workspace=self.request.workspace)
            .select_related(
                "installment__subscription__customer",
                "recorded_by",
                "approved_by",
            )
            .order_by("-created_at")
        )


@method_decorator(name="retrieve", decorator=swagger_auto_schema(tags=_PAY_TAG))
class PaymentDetailView(generics.RetrieveAPIView):
    """GET /api/v1/payments/<id>/"""

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return Payment.objects.filter(workspace=self.request.workspace).select_related(
            "installment__subscription__customer",
            "recorded_by",
            "approved_by",
        )


class RecordPaymentView(APIView):
    """
    POST /api/v1/payments/record/

    Record a new payment against an installment.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    @swagger_auto_schema(
        tags=_PAY_TAG,
        request_body=RecordPaymentSerializer,
        responses={201: PaymentSerializer},
        operation_description="Record a new payment against an installment.",
    )
    def post(self, request):
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            installment = Installment.objects.get(
                id=data["installment_id"],
                workspace=request.workspace,
            )
        except Installment.DoesNotExist:
            return Response(
                {"message": "Installment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = PaymentService.record_payment(
                workspace=request.workspace,
                installment=installment,
                amount=data["amount"],
                recorded_by=request.user,
                receipt_url=data.get("receipt_url", ""),
                receipt_file=data.get("receipt_file"),
                notes=data.get("notes", ""),
            )
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED,
        )


class ApprovePaymentView(APIView):
    """
    POST /api/v1/payments/<id>/approve/

    Approve a pending payment.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=_PAY_TAG)
    def post(self, request, id):
        try:
            payment = Payment.objects.get(id=id, workspace=request.workspace)
        except Payment.DoesNotExist:
            return Response(
                {"message": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = PaymentService.approve_payment(payment, approved_by=request.user)
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PaymentSerializer(payment).data)


class RejectPaymentView(APIView):
    """
    POST /api/v1/payments/<id>/reject/

    Reject a pending payment.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=_PAY_TAG)
    def post(self, request, id):
        serializer = ApproveRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment = Payment.objects.get(id=id, workspace=request.workspace)
        except Payment.DoesNotExist:
            return Response(
                {"message": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            payment = PaymentService.reject_payment(
                payment, reason=serializer.validated_data.get("reason", "")
            )
        except ValueError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(PaymentSerializer(payment).data)


# ---------------------------------------------------------------------------
# Paystack — Bank Account Verification
# ---------------------------------------------------------------------------

class ResolveAccountView(APIView):
    """
    GET /api/v1/payments/verify-account/?account_number=<num>&bank_code=<code>

    Calls Paystack's resolve account API to verify a bank account number.
    Returns { account_name, account_number } on success.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        import json as _json
        import logging
        import urllib3
        from django.conf import settings

        logger = logging.getLogger(__name__)

        account_number = request.query_params.get("account_number", "").strip()
        bank_code = request.query_params.get("bank_code", "").strip()

        if not account_number or not bank_code:
            return Response(
                {"message": "account_number and bank_code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret_key:
            return Response(
                {"message": "Payment gateway not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        url = (
            f"https://api.paystack.co/bank/resolve"
            f"?account_number={account_number}&bank_code={bank_code}"
        )
        http = urllib3.PoolManager()
        try:
            resp = http.request(
                "GET",
                url,
                headers={
                    "Authorization": f"Bearer {secret_key}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            raw = resp.data.decode("utf-8", errors="replace").strip()
            logger.debug("Paystack resolve status=%s body=%s", resp.status, raw[:500])

            if resp.status == 200:
                data = _json.loads(raw)
                if data.get("status"):
                    return Response({
                        "account_name": data["data"]["account_name"],
                        "account_number": data["data"]["account_number"],
                    })
                return Response(
                    {"message": data.get("message", "Verification failed.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Non-200 response from Paystack
            try:
                body = _json.loads(raw) if raw else {}
            except Exception:
                body = {}
            msg = body.get("message", "")
            logger.warning(
                "Paystack resolve returned %s for account=%s bank=%s: %s",
                resp.status, account_number, bank_code, msg or raw[:200],
            )
            return Response(
                {"message": msg or "Account verification failed. Check the account number and bank, then try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        except urllib3.exceptions.MaxRetryError as e:
            logger.error("Paystack resolve connection error: %s", e)
            return Response(
                {"message": "Could not reach payment gateway. Check your internet connection and try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.error("Paystack resolve unexpected error: %s", e)
            return Response(
                {"message": "Could not reach payment gateway. Try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class PaystackBanksListView(APIView):
    """
    GET /api/v1/payments/banks/

    Returns list of Nigerian banks from Paystack.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        import json as _json
        import logging
        import urllib3
        from django.conf import settings

        logger = logging.getLogger(__name__)
        secret_key = getattr(settings, "PAYSTACK_SECRET_KEY", "")
        if not secret_key:
            return Response({"message": "Payment gateway not configured."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        http = urllib3.PoolManager()
        try:
            resp = http.request(
                "GET",
                "https://api.paystack.co/bank?country=nigeria&perPage=100",
                headers={
                    "Authorization": f"Bearer {secret_key}",
                    "Accept": "application/json",
                },
                timeout=10.0,
            )
            raw = resp.data.decode("utf-8", errors="replace").strip()
            if resp.status == 200:
                data = _json.loads(raw) if raw else {}
                banks = [{"name": b["name"], "code": b["code"]} for b in data.get("data", [])]
                return Response({"banks": banks})
            try:
                body = _json.loads(raw) if raw else {}
            except Exception:
                body = {}
            logger.warning("Paystack banks returned %s: %s", resp.status, raw[:200])
            return Response({"message": body.get("message", "Could not fetch bank list.")}, status=status.HTTP_502_BAD_GATEWAY)
        except urllib3.exceptions.MaxRetryError as e:
            logger.error("Paystack banks connection error: %s", e)
            return Response({"message": "Could not fetch bank list."}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            logger.error("Paystack banks unexpected error: %s", e)
            return Response({"message": "Could not fetch bank list."}, status=status.HTTP_502_BAD_GATEWAY)
