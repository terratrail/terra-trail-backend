"""
Payments views — Record, approve, reject payments.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from customers.models import Installment
from payments.models import Payment
from payments.serializers import (
    ApproveRejectSerializer,
    PaymentSerializer,
    RecordPaymentSerializer,
)
from payments.services import PaymentService


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
