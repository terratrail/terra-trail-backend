"""
Bulk upload views for Site Inspections, Subscriptions, and Installments.

POST /api/v1/customers/inspections/bulk-upload/
POST /api/v1/customers/subscriptions/bulk-upload/
POST /api/v1/customers/installments/bulk-upload/

GET  /api/v1/customers/inspections/bulk-upload/template/
GET  /api/v1/customers/subscriptions/bulk-upload/template/
GET  /api/v1/customers/installments/bulk-upload/template/
"""

import csv
import io

from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsWorkspaceAdminOrReadOnly

# ---------------------------------------------------------------------------
# Generic CSV/xlsx parser helper (identical logic to existing bulk views)
# ---------------------------------------------------------------------------

def _parse_rows(file_obj, filename: str, first_col: str):
    name = filename.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        try:
            import openpyxl
        except ImportError:
            raise ValueError("openpyxl is required for Excel uploads. Use CSV instead.")
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip().lower() if h else "" for h in rows[0]]
        data_rows = []
        for row in rows[1:]:
            d = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
            if all(not v for v in d.values()):
                continue
            data_rows.append(d)
        return data_rows
    else:
        text = file_obj.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            d = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items()}
            if d.get(first_col, "").startswith("#"):
                continue
            rows.append(d)
        return rows


def _simple_csv_response(columns, sample_rows, filename):
    """Generate a simple CSV template response."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    headers = [c[0] for c in columns]
    writer.writerow(headers)
    writer.writerow([
        f"# {'REQUIRED' if c[1] else 'optional'} — {c[2]}{(' Valid: ' + c[3]) if c[3] else ''}"
        for c in columns
    ])
    for row in sample_rows:
        writer.writerow(row)
    response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _check_file(request):
    """Return (file, error_response) from request."""
    f = request.FILES.get("file")
    if not f:
        return None, Response({"detail": "No file provided."}, status=400)
    return f, None


# ===========================================================================
# Site Inspections
# ===========================================================================

INSPECTION_COLUMNS = [
    ("name",             True,  "Contact/visitor name",                                    None,                         "Chidi Okafor"),
    ("phone",            False, "Contact phone number",                                    None,                         "+2348012345678"),
    ("email",            False, "Contact email address",                                   None,                         "chidi@email.com"),
    ("property_name",    True,  "Property name (must match an existing property exactly)", None,                         "Sunset Gardens Phase 1"),
    ("inspection_date",  True,  "Date of inspection (YYYY-MM-DD)",                         None,                         "2025-06-15"),
    ("inspection_time",  False, "Time of inspection (HH:MM, 24h)",                        None,                         "10:00"),
    ("inspection_type",  False, "Type of inspection. Defaults to PHYSICAL.",               "PHYSICAL|VIRTUAL",           "PHYSICAL"),
    ("category",         False, "Property category. Defaults to RESIDENTIAL.",             "RESIDENTIAL|COMMERCIAL|FARM_LAND", "RESIDENTIAL"),
    ("notes",            False, "Additional notes",                                        None,                         "Client prefers morning slots"),
]

INSPECTION_SAMPLE_ROWS = [
    ["Chidi Okafor",    "+2348012345678", "chidi@email.com",   "Sunset Gardens Phase 1",   "2025-06-15", "10:00", "PHYSICAL", "RESIDENTIAL", ""],
    ["Amina Yusuf",     "+2347098765432", "amina@yahoo.com",   "Green Valley Farm Estate", "2025-06-20", "14:00", "VIRTUAL",  "FARM_LAND",   "Virtual tour preferred"],
    ["Kunle Adeyemi",   "+2349012345678", "kunle@gmail.com",   "Sunset Gardens Phase 1",   "2025-06-22", "",      "PHYSICAL", "RESIDENTIAL", ""],
]


class SiteInspectionBulkUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from customers.site_inspection_models import SiteInspection
        from properties.models import Property

        file, err = _check_file(request)
        if err:
            return err

        try:
            rows = _parse_rows(file, file.name, "name")
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not rows:
            return Response({"detail": "The file contains no data rows."}, status=400)
        if len(rows) > 500:
            return Response({"detail": "Maximum 500 rows per upload. Please split your file."}, status=400)

        created = 0
        skipped = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            name = row.get("name", "").strip()
            property_name = row.get("property_name", "").strip()
            inspection_date = row.get("inspection_date", "").strip()

            if not name:
                errors.append({"row": idx, "error": "name is required"})
                continue
            if not property_name:
                errors.append({"row": idx, "error": "property_name is required"})
                continue
            if not inspection_date:
                errors.append({"row": idx, "error": "inspection_date is required"})
                continue

            # Parse date
            try:
                from datetime import date
                inspection_date_obj = date.fromisoformat(inspection_date)
            except ValueError:
                errors.append({"row": idx, "error": f"invalid inspection_date '{inspection_date}' — use YYYY-MM-DD"})
                continue

            # Look up property (optional link)
            linked_property = None
            try:
                linked_property = Property.objects.get(
                    workspace=request.workspace, name__iexact=property_name
                )
            except Property.DoesNotExist:
                pass  # store as free-text

            # Parse time
            inspection_time = None
            raw_time = row.get("inspection_time", "").strip()
            if raw_time:
                try:
                    from datetime import time as time_type
                    parts = raw_time.split(":")
                    inspection_time = time_type(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
                except Exception:
                    pass  # ignore bad time, not required

            # Parse inspection_type
            raw_type = row.get("inspection_type", "").strip().upper()
            inspection_type = raw_type if raw_type in ("PHYSICAL", "VIRTUAL") else "PHYSICAL"

            # Parse category
            raw_cat = row.get("category", "").strip().upper()
            category = raw_cat if raw_cat in ("RESIDENTIAL", "COMMERCIAL", "FARM_LAND") else "RESIDENTIAL"

            # No strict dedup — just create
            try:
                SiteInspection.objects.create(
                    workspace=request.workspace,
                    name=name,
                    phone=row.get("phone", "").strip(),
                    email=row.get("email", "").strip().lower(),
                    linked_property=linked_property,
                    property_name=property_name,
                    inspection_date=inspection_date_obj,
                    inspection_time=inspection_time,
                    inspection_type=inspection_type,
                    category=category,
                    notes=row.get("notes", "").strip(),
                )
                created += 1
            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        return Response({
            "total_rows": len(rows),
            "created": created,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors,
        })


class SiteInspectionBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return _simple_csv_response(
            INSPECTION_COLUMNS,
            INSPECTION_SAMPLE_ROWS,
            "terratrail_inspections_template.csv",
        )


# ===========================================================================
# Subscriptions
# ===========================================================================

SUBSCRIPTION_COLUMNS = [
    ("customer_email",   True,  "Email of existing customer",                              None,                               "adebayo.johnson@email.com"),
    ("property_name",    True,  "Name of the property (must exist in workspace)",          None,                               "Sunset Gardens Phase 1"),
    ("plan_name",        True,  "Pricing plan name (must exist and be active)",            None,                               "Standard Plot - 12 months"),
    ("notes",            False, "Subscription notes",                                      None,                               "Referred by Sales Rep Tunde"),
]

SUBSCRIPTION_SAMPLE_ROWS = [
    ["adebayo.johnson@email.com",  "Sunset Gardens Phase 1",   "Standard Plot - 12 months", "Referred by agent"],
    ["chidinma.okafor@gmail.com",  "Green Valley Farm Estate", "Premium Plot - Outright",   ""],
    ["emeka.eze@company.ng",       "Sunset Gardens Phase 1",   "Budget Plot - 24 months",   "VIP customer"],
]


class SubscriptionBulkUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from customers.models import Customer, Subscription
        from customers.services import SubscriptionService
        from properties.models import Property, PricingPlan

        file, err = _check_file(request)
        if err:
            return err

        try:
            rows = _parse_rows(file, file.name, "customer_email")
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not rows:
            return Response({"detail": "The file contains no data rows."}, status=400)
        if len(rows) > 500:
            return Response({"detail": "Maximum 500 rows per upload. Please split your file."}, status=400)

        created = 0
        skipped = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            customer_email = row.get("customer_email", "").strip().lower()
            property_name  = row.get("property_name", "").strip()
            plan_name      = row.get("plan_name", "").strip()

            if not customer_email:
                errors.append({"row": idx, "error": "customer_email is required"})
                continue
            if not property_name:
                errors.append({"row": idx, "error": "property_name is required"})
                continue
            if not plan_name:
                errors.append({"row": idx, "error": "plan_name is required"})
                continue

            # Resolve customer
            try:
                customer = Customer.objects.get(workspace=request.workspace, email__iexact=customer_email)
            except Customer.DoesNotExist:
                errors.append({"row": idx, "error": f"customer not found: '{customer_email}'"})
                continue

            # Resolve property
            try:
                prop = Property.objects.get(workspace=request.workspace, name__iexact=property_name)
            except Property.DoesNotExist:
                errors.append({"row": idx, "error": f"property not found: '{property_name}'"})
                continue

            # Resolve pricing plan
            try:
                plan = PricingPlan.objects.get(
                    workspace=request.workspace,
                    property=prop,
                    name__iexact=plan_name,
                    is_active=True,
                )
            except PricingPlan.DoesNotExist:
                # Try without is_active filter
                try:
                    plan = PricingPlan.objects.get(
                        workspace=request.workspace,
                        property=prop,
                        name__iexact=plan_name,
                    )
                except PricingPlan.DoesNotExist:
                    errors.append({"row": idx, "error": f"pricing plan not found: '{plan_name}' on '{property_name}'"})
                    continue

            # Dedup: skip if subscription already exists for customer+property+plan
            if Subscription.objects.filter(
                workspace=request.workspace,
                customer=customer,
                property=prop,
                pricing_plan=plan,
            ).exclude(status=Subscription.Status.CANCELLED).exists():
                skipped += 1
                continue

            try:
                SubscriptionService.create_subscription(
                    workspace=request.workspace,
                    customer=customer,
                    property_obj=prop,
                    pricing_plan=plan,
                    notes=row.get("notes", "").strip(),
                )
                created += 1
            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        return Response({
            "total_rows": len(rows),
            "created": created,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors,
        })


class SubscriptionBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return _simple_csv_response(
            SUBSCRIPTION_COLUMNS,
            SUBSCRIPTION_SAMPLE_ROWS,
            "terratrail_subscriptions_template.csv",
        )


# ===========================================================================
# Installments
# ===========================================================================

INSTALLMENT_COLUMNS = [
    ("subscription_id",    False, "UUID of the subscription. If blank, use customer_email + property_name to look up.",  None, "3fa85f64-5717-4562-b3fc-2c963f66afa6"),
    ("customer_email",     False, "Customer email — used to look up subscription if subscription_id is blank.",          None, "adebayo.johnson@email.com"),
    ("property_name",      False, "Property name — used with customer_email to look up subscription.",                   None, "Sunset Gardens Phase 1"),
    ("due_date",           True,  "Due date for this installment (YYYY-MM-DD)",                                          None, "2025-07-01"),
    ("amount",             True,  "Installment amount (numeric, e.g. 150000)",                                           None, "150000"),
    ("installment_number", False, "Installment number in sequence. Auto-assigned if blank.",                             None, "3"),
    ("notes",              False, "Optional notes",                                                                      None, ""),
]

INSTALLMENT_SAMPLE_ROWS = [
    ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "",                           "",                         "2025-07-01", "150000", "1", ""],
    ["",                                      "chidinma.okafor@gmail.com",  "Green Valley Farm Estate", "2025-08-01", "150000", "2", ""],
    ["",                                      "emeka.eze@company.ng",       "Sunset Gardens Phase 1",   "2025-09-01", "200000", "1", "Second instalment"],
]


class InstallmentBulkUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        from customers.models import Customer, Subscription, Installment
        from properties.models import Property

        file, err = _check_file(request)
        if err:
            return err

        try:
            rows = _parse_rows(file, file.name, "subscription_id")
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not rows:
            return Response({"detail": "The file contains no data rows."}, status=400)
        if len(rows) > 500:
            return Response({"detail": "Maximum 500 rows per upload. Please split your file."}, status=400)

        created = 0
        skipped = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            due_date_raw = row.get("due_date", "").strip()
            amount_raw   = row.get("amount", "").strip()

            if not due_date_raw:
                errors.append({"row": idx, "error": "due_date is required"})
                continue
            if not amount_raw:
                errors.append({"row": idx, "error": "amount is required"})
                continue

            # Parse date
            try:
                from datetime import date
                due_date = date.fromisoformat(due_date_raw)
            except ValueError:
                errors.append({"row": idx, "error": f"invalid due_date '{due_date_raw}' — use YYYY-MM-DD"})
                continue

            # Parse amount
            try:
                amount = Decimal(amount_raw.replace(",", ""))
            except InvalidOperation:
                errors.append({"row": idx, "error": f"invalid amount '{amount_raw}'"})
                continue

            # Resolve subscription
            subscription = None
            sub_id = row.get("subscription_id", "").strip()
            if sub_id:
                try:
                    subscription = Subscription.objects.get(id=sub_id, workspace=request.workspace)
                except (Subscription.DoesNotExist, Exception):
                    errors.append({"row": idx, "error": f"subscription not found: '{sub_id}'"})
                    continue
            else:
                customer_email = row.get("customer_email", "").strip().lower()
                property_name  = row.get("property_name", "").strip()
                if not customer_email or not property_name:
                    errors.append({"row": idx, "error": "subscription_id or (customer_email + property_name) is required"})
                    continue
                try:
                    customer = Customer.objects.get(workspace=request.workspace, email__iexact=customer_email)
                    prop = Property.objects.get(workspace=request.workspace, name__iexact=property_name)
                    subscription = Subscription.objects.filter(
                        workspace=request.workspace,
                        customer=customer,
                        property=prop,
                    ).exclude(status=Subscription.Status.CANCELLED).order_by("-created_at").first()
                    if not subscription:
                        errors.append({"row": idx, "error": f"no active subscription found for '{customer_email}' on '{property_name}'"})
                        continue
                except Customer.DoesNotExist:
                    errors.append({"row": idx, "error": f"customer not found: '{customer_email}'"})
                    continue
                except Property.DoesNotExist:
                    errors.append({"row": idx, "error": f"property not found: '{property_name}'"})
                    continue

            # Dedup: same subscription + due_date + amount
            if Installment.objects.filter(
                workspace=request.workspace,
                subscription=subscription,
                due_date=due_date,
                amount=amount,
            ).exists():
                skipped += 1
                continue

            # Determine installment number
            installment_number_raw = row.get("installment_number", "").strip()
            if installment_number_raw:
                try:
                    installment_number = int(installment_number_raw)
                except ValueError:
                    installment_number = None
            else:
                installment_number = None

            if installment_number is None:
                last = Installment.objects.filter(
                    workspace=request.workspace, subscription=subscription
                ).order_by("-installment_number").first()
                installment_number = (last.installment_number + 1) if last else 1

            try:
                Installment.objects.create(
                    workspace=request.workspace,
                    subscription=subscription,
                    due_date=due_date,
                    amount=amount,
                    installment_number=installment_number,
                )
                created += 1
            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        return Response({
            "total_rows": len(rows),
            "created": created,
            "skipped": skipped,
            "error_count": len(errors),
            "errors": errors,
        })


class InstallmentBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return _simple_csv_response(
            INSTALLMENT_COLUMNS,
            INSTALLMENT_SAMPLE_ROWS,
            "terratrail_installments_template.csv",
        )
