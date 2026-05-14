"""
Bulk upload views for Payments (CSV / Excel).

POST /api/v1/payments/bulk-upload/
GET  /api/v1/payments/bulk-upload/template/

Payment bulk upload links each row to an Installment via:
  - installment_id (UUID), OR
  - subscription_id + installment_number, OR
  - customer_email + property_name + installment_number

Records are created with status PENDING. Approve them individually.
"""

import csv
import io
import secrets

from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsWorkspaceAdminOrReadOnly


PAYMENT_COLUMNS = [
    ("installment_id",    False, "UUID of the installment. If blank, use subscription_id + installment_number.",         None, "3fa85f64-5717-4562-b3fc-2c963f66afa6"),
    ("subscription_id",   False, "UUID of the subscription. Used with installment_number if installment_id is blank.",  None, "7c9e6679-7425-40de-944b-e07fc1f90ae7"),
    ("customer_email",    False, "Customer email — alternative lookup with property_name + installment_number.",         None, "adebayo.johnson@email.com"),
    ("property_name",     False, "Property name — used with customer_email for lookup.",                                 None, "Sunset Gardens Phase 1"),
    ("installment_number",False, "Installment number — used when installment_id is blank.",                              None, "1"),
    ("amount",            True,  "Payment amount (numeric, e.g. 150000)",                                                None, "150000"),
    ("payment_date",      False, "Date of payment (YYYY-MM-DD). Defaults to today if blank.",                           None, "2025-06-01"),
    ("reference",         False, "Transaction reference. Auto-generated if blank.",                                      None, "TXN-001"),
    ("notes",             False, "Optional notes",                                                                       None, ""),
]

PAYMENT_SAMPLE_ROWS = [
    ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "",                                    "",                           "",                         "",  "150000", "2025-06-01", "TXN-001", ""],
    ["",                                      "7c9e6679-7425-40de-944b-e07fc1f90ae7", "",                           "",                         "2", "150000", "2025-07-01", "",        ""],
    ["",                                      "",                                    "chidinma.okafor@gmail.com",   "Green Valley Farm Estate", "1", "200000", "2025-06-15", "TXN-003", "VIP"],
]


def _parse_rows(file_obj, filename: str):
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
            if d.get("installment_id", "").startswith("#"):
                continue
            rows.append(d)
        return rows


class PaymentBulkUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from decimal import Decimal, InvalidOperation
        from datetime import date as date_type
        from customers.models import Customer, Subscription, Installment
        from payments.models import Payment
        from properties.models import Property

        file = request.FILES.get("file")
        if not file:
            return Response({"detail": "No file provided."}, status=400)

        try:
            rows = _parse_rows(file, file.name)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)

        if not rows:
            return Response({"detail": "The file contains no data rows."}, status=400)
        if len(rows) > 500:
            return Response({"detail": "Maximum 500 rows per upload. Please split your file."}, status=400)

        created = 0
        skipped = 0
        errors = []
        today = date_type.today()

        for idx, row in enumerate(rows, start=2):
            amount_raw = row.get("amount", "").strip()
            if not amount_raw:
                errors.append({"row": idx, "error": "amount is required"})
                continue

            try:
                amount = Decimal(amount_raw.replace(",", ""))
            except InvalidOperation:
                errors.append({"row": idx, "error": f"invalid amount '{amount_raw}'"})
                continue

            # Resolve installment
            installment = None
            installment_id = row.get("installment_id", "").strip()
            if installment_id:
                try:
                    installment = Installment.objects.get(id=installment_id, workspace=request.workspace)
                except (Installment.DoesNotExist, Exception):
                    errors.append({"row": idx, "error": f"installment not found: '{installment_id}'"})
                    continue
            else:
                # Try via subscription_id + installment_number
                sub_id = row.get("subscription_id", "").strip()
                inst_num_raw = row.get("installment_number", "").strip()

                subscription = None
                if sub_id:
                    try:
                        subscription = Subscription.objects.get(id=sub_id, workspace=request.workspace)
                    except (Subscription.DoesNotExist, Exception):
                        errors.append({"row": idx, "error": f"subscription not found: '{sub_id}'"})
                        continue
                else:
                    # Try via customer_email + property_name
                    customer_email = row.get("customer_email", "").strip().lower()
                    property_name  = row.get("property_name", "").strip()
                    if customer_email and property_name:
                        try:
                            customer = Customer.objects.get(workspace=request.workspace, email__iexact=customer_email)
                            prop = Property.objects.get(workspace=request.workspace, name__iexact=property_name)
                            subscription = Subscription.objects.filter(
                                workspace=request.workspace,
                                customer=customer,
                                property=prop,
                            ).exclude(status=Subscription.Status.CANCELLED).order_by("-created_at").first()
                            if not subscription:
                                errors.append({"row": idx, "error": f"no active subscription for '{customer_email}' / '{property_name}'"})
                                continue
                        except Customer.DoesNotExist:
                            errors.append({"row": idx, "error": f"customer not found: '{customer_email}'"})
                            continue
                        except Property.DoesNotExist:
                            errors.append({"row": idx, "error": f"property not found: '{property_name}'"})
                            continue
                    else:
                        errors.append({"row": idx, "error": "installment_id or (subscription_id or customer_email+property_name) is required"})
                        continue

                if subscription and inst_num_raw:
                    try:
                        inst_num = int(inst_num_raw)
                        installment = Installment.objects.filter(
                            workspace=request.workspace,
                            subscription=subscription,
                            installment_number=inst_num,
                        ).first()
                        if not installment:
                            errors.append({"row": idx, "error": f"installment #{inst_num} not found on subscription"})
                            continue
                    except ValueError:
                        errors.append({"row": idx, "error": f"invalid installment_number '{inst_num_raw}'"})
                        continue
                elif subscription:
                    # No installment number — pick the oldest unpaid installment
                    installment = Installment.objects.filter(
                        workspace=request.workspace,
                        subscription=subscription,
                    ).exclude(status=Installment.Status.PAID).order_by("installment_number").first()
                    if not installment:
                        errors.append({"row": idx, "error": "no unpaid installment found for subscription"})
                        continue

            # Parse payment date
            payment_date_raw = row.get("payment_date", "").strip()
            if payment_date_raw:
                try:
                    payment_date = date_type.fromisoformat(payment_date_raw)
                except ValueError:
                    payment_date = today
            else:
                payment_date = today

            # Reference
            reference = row.get("reference", "").strip()
            if not reference:
                reference = f"BULK-{secrets.token_hex(6).upper()}"

            # Dedup by reference
            if Payment.objects.filter(transaction_reference=reference).exists():
                skipped += 1
                continue

            try:
                Payment.objects.create(
                    workspace=request.workspace,
                    installment=installment,
                    amount=amount,
                    payment_date=payment_date,
                    transaction_reference=reference,
                    notes=row.get("notes", "").strip(),
                    recorded_by=request.user,
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


class PaymentBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        buf = io.StringIO()
        writer = csv.writer(buf)
        headers = [c[0] for c in PAYMENT_COLUMNS]
        writer.writerow(headers)
        writer.writerow([
            f"# {'REQUIRED' if c[1] else 'optional'} — {c[2]}{(' Valid: ' + c[3]) if c[3] else ''}"
            for c in PAYMENT_COLUMNS
        ])
        for row in PAYMENT_SAMPLE_ROWS:
            writer.writerow(row)
        response = HttpResponse(buf.getvalue(), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="terratrail_payments_template.csv"'
        return response
