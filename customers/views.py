"""
Customers views — CRUD for customers and subscriptions.
"""

from django.utils.decorators import method_decorator
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

_CUST_TAG = ["Customers"]

from core.permissions import IsWorkspaceAdmin, IsWorkspaceAdminOrReadOnly
from core.plan_guard import PlanGuard, PlanLimitExceeded
from customers.models import Customer, Installment, Subscription
from customers.serializers import (
    CustomerCreateSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerSerializer,
    InstallmentSerializer,
    SubscriptionListSerializer,
    SubscriptionSerializer,
)
from customers.services import SubscriptionService
from properties.models import PricingPlan, Property


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_CUST_TAG))
class CustomerListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/customers/          — List customers
    POST /api/v1/customers/          — Create a customer (optionally with subscription)
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    filterset_fields = ["referral_source"]
    search_fields = ["full_name", "email", "phone"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CustomerCreateSerializer
        return CustomerListSerializer

    def get_queryset(self):
        return (
            Customer.objects.filter(workspace=self.request.workspace)
            .prefetch_related("subscriptions__pricing_plan", "subscriptions__installments", "subscriptions__property")
            .order_by("-created_at")
        )

    @swagger_auto_schema(
        tags=_CUST_TAG,
        request_body=CustomerCreateSerializer,
        responses={201: CustomerSerializer},
        operation_description="Create a customer (optionally with subscription).",
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        property_id = data.pop("property_id", None)
        pricing_plan_id = data.pop("pricing_plan_id", None)

        # Enforce plan limit before creating
        try:
            PlanGuard.check_customer_limit(request.workspace)
        except PlanLimitExceeded as e:
            return Response({"message": str(e)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        # Create customer
        customer = Customer.objects.create(workspace=request.workspace, **data)

        response_data = CustomerSerializer(customer).data

        # Optionally create subscription
        if property_id and pricing_plan_id:
            try:
                property_obj = Property.objects.get(
                    id=property_id, workspace=request.workspace
                )
                pricing_plan = PricingPlan.objects.get(
                    id=pricing_plan_id,
                    workspace=request.workspace,
                    is_active=True,
                )
                subscription = SubscriptionService.create_subscription(
                    workspace=request.workspace,
                    customer=customer,
                    property_obj=property_obj,
                    pricing_plan=pricing_plan,
                )
                response_data["subscription"] = SubscriptionSerializer(
                    subscription
                ).data
            except (Property.DoesNotExist, PricingPlan.DoesNotExist) as e:
                return Response(
                    {
                        "message": "Invalid property or pricing plan.",
                        "customer": response_data,
                    },
                    status=status.HTTP_201_CREATED,
                )

        return Response(response_data, status=status.HTTP_201_CREATED)


@method_decorator(name="retrieve",       decorator=swagger_auto_schema(tags=_CUST_TAG))
@method_decorator(name="update",         decorator=swagger_auto_schema(tags=_CUST_TAG))
@method_decorator(name="partial_update", decorator=swagger_auto_schema(tags=_CUST_TAG))
@method_decorator(name="destroy",        decorator=swagger_auto_schema(tags=_CUST_TAG))
class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PATCH/DELETE /api/v1/customers/<id>/"""

    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method == "GET":
            return CustomerDetailSerializer
        return CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(
            workspace=self.request.workspace
        ).prefetch_related(
            "subscriptions__property",
            "subscriptions__pricing_plan",
        )


# ---------------------------------------------------------------------------
# Subscription endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_CUST_TAG))
class SubscriptionListView(generics.ListAPIView):
    """GET /api/v1/customers/subscriptions/"""

    serializer_class = SubscriptionListSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    filterset_fields = ["status", "customer", "property", "assigned_rep"]

    def get_queryset(self):
        return (
            Subscription.objects.filter(workspace=self.request.workspace)
            .select_related("customer", "property", "pricing_plan", "assigned_rep")
            .order_by("-created_at")
        )


@method_decorator(name="retrieve", decorator=swagger_auto_schema(tags=_CUST_TAG))
@method_decorator(name="destroy",  decorator=swagger_auto_schema(tags=_CUST_TAG))
class SubscriptionDetailView(generics.RetrieveDestroyAPIView):
    """GET/DELETE /api/v1/customers/subscriptions/<id>/"""

    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    lookup_field = "id"

    def get_queryset(self):
        return (
            Subscription.objects.filter(workspace=self.request.workspace)
            .select_related("customer", "property", "pricing_plan")
            .prefetch_related("installments")
        )

    def perform_destroy(self, instance):
        deletable = [
            Subscription.Status.PENDING,
            Subscription.Status.ACTIVE,
            Subscription.Status.DEFAULTED,
            Subscription.Status.DEFAULTING,
        ]
        if instance.status not in deletable:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only pending, active, or defaulting subscriptions can be deleted.")
        instance.delete()


class SubscriptionCreateView(APIView):
    """
    POST /api/v1/customers/subscriptions/create/

    Create a subscription for an existing customer.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(
        tags=_CUST_TAG,
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["customer_id", "property_id", "pricing_plan_id"],
            properties={
                "customer_id": openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
                ),
                "property_id": openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
                ),
                "pricing_plan_id": openapi.Schema(
                    type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID
                ),
                "notes": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={201: SubscriptionSerializer},
        operation_description="Create a subscription for an existing customer.",
    )
    def post(self, request):
        customer_id = request.data.get("customer_id")
        property_id = request.data.get("property_id")
        pricing_plan_id = request.data.get("pricing_plan_id")
        notes = request.data.get("notes", "")

        if not all([customer_id, property_id, pricing_plan_id]):
            return Response(
                {
                    "message": "customer_id, property_id, and pricing_plan_id are required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            customer = Customer.objects.get(id=customer_id, workspace=request.workspace)
            property_obj = Property.objects.get(
                id=property_id, workspace=request.workspace
            )
            pricing_plan = PricingPlan.objects.get(
                id=pricing_plan_id, workspace=request.workspace, is_active=True
            )
        except (Customer.DoesNotExist, Property.DoesNotExist, PricingPlan.DoesNotExist):
            return Response(
                {"message": "Invalid customer, property, or pricing plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = SubscriptionService.create_subscription(
            workspace=request.workspace,
            customer=customer,
            property_obj=property_obj,
            pricing_plan=pricing_plan,
            notes=notes,
        )

        # Auto-convert matching site inspections
        from customers.site_inspection_models import SiteInspection
        from django.db import models as _models
        SiteInspection.objects.filter(
            workspace=subscription.workspace,
            converted_customer__isnull=True,
        ).filter(
            _models.Q(email__iexact=customer.email) |
            _models.Q(phone=customer.phone)
        ).update(converted_customer=customer)

        try:
            from notifications.services import NotificationService
            NotificationService.send_subscription_confirmation_email(subscription)
        except Exception:
            pass

        return Response(
            SubscriptionSerializer(subscription).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Installment endpoints
# ---------------------------------------------------------------------------


@method_decorator(name="list", decorator=swagger_auto_schema(tags=_CUST_TAG))
class InstallmentListView(generics.ListAPIView):
    """
    GET /api/v1/customers/installments/

    List installments, filterable by subscription and status.
    """

    serializer_class = InstallmentSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]
    filterset_fields = ["status", "subscription"]

    def get_queryset(self):
        return (
            Installment.objects.filter(workspace=self.request.workspace)
            .select_related("subscription")
            .order_by("due_date")
        )


class AllocateSubscriptionView(APIView):
    """
    POST /api/v1/customers/subscriptions/<id>/allocate/

    Assign a plot number to a completed subscription.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=["Subscriptions"])
    def post(self, request, id):
        try:
            subscription = Subscription.objects.get(id=id, workspace=request.workspace)
        except Subscription.DoesNotExist:
            return Response({"message": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        if subscription.status != Subscription.Status.COMPLETED:
            return Response(
                {"message": "Plot can only be allocated to completed subscriptions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plot_number = request.data.get("plot_number", "").strip()
        allocation_date = request.data.get("allocation_date")
        allocation_notes = request.data.get("allocation_notes", "")
        allocation_letter = request.FILES.get("allocation_letter")

        if not plot_number:
            return Response({"message": "Plot number is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not allocation_date:
            return Response({"message": "Allocation date is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Duplicate plot check within the same property
        duplicate = Subscription.objects.filter(
            workspace=request.workspace,
            property=subscription.property,
            plot_number=plot_number,
        ).exclude(id=subscription.id).first()
        if duplicate:
            return Response(
                {"message": f"Plot '{plot_number}' is already allocated to another customer in this property."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription.plot_number = plot_number
        subscription.allocation_date = allocation_date
        subscription.allocation_notes = allocation_notes
        if allocation_letter:
            subscription.allocation_letter = allocation_letter
        subscription.save(update_fields=["plot_number", "allocation_date", "allocation_notes", "allocation_letter", "updated_at"])

        return Response(SubscriptionListSerializer(subscription).data)


class CancelSubscriptionView(APIView):
    """
    POST /api/v1/customers/subscriptions/<id>/cancel/

    Cancel a subscription. Only PENDING/ACTIVE/DEFAULTING/DEFAULTED.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceAdmin]

    @swagger_auto_schema(tags=["Subscriptions"])
    def post(self, request, id):
        try:
            subscription = Subscription.objects.get(id=id, workspace=request.workspace)
        except Subscription.DoesNotExist:
            return Response({"message": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND)

        cancellable = [
            Subscription.Status.PENDING,
            Subscription.Status.ACTIVE,
            Subscription.Status.DEFAULTED,
            Subscription.Status.DEFAULTING,
        ]
        if subscription.status not in cancellable:
            return Response(
                {"message": "Only pending, active, or defaulting subscriptions can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "").strip()
        subscription.status = Subscription.Status.CANCELLED
        if reason:
            subscription.notes = f"{subscription.notes}\nCancellation reason: {reason}".strip()
        subscription.save(update_fields=["status", "notes", "updated_at"])

        return Response(SubscriptionListSerializer(subscription).data)
