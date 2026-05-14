"""
Bulk upload views for Sales Reps and Customer Reps (CSV / Excel).

POST /api/v1/commissions/reps/bulk-upload/
GET  /api/v1/commissions/reps/bulk-upload/template/

POST /api/v1/commissions/customer-reps/bulk-upload/
GET  /api/v1/commissions/customer-reps/bulk-upload/template/

Sales Reps are created as SalesRep model entries (commissions app).
Customer Reps are created as WorkspaceMembership entries with role CUSTOMER_REP
(and a User account with unusable password if the email doesn't exist yet).
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
            if d.get("name", "").startswith("#"):
                continue
            rows.append(d)
        return rows


def _simple_csv_response(columns, sample_rows, filename):
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


# ===========================================================================
# Sales Reps
# ===========================================================================

SALES_REP_COLUMNS = [
    ("name",           True,  "Full name of the sales rep",                              None,                      "Tunde Ogundimu"),
    ("email",          True,  "Email address (unique per workspace, used for dedup)",    None,                      "tunde@email.com"),
    ("phone",          True,  "Phone number",                                            None,                      "+2348056789012"),
    ("tier",           False, "Rep tier. Defaults to STARTER.",                          "STARTER|SENIOR|LEGEND",   "STARTER"),
    ("referral_code",  False, "Unique referral code. Auto-generated if blank.",          None,                      "TUNDE001"),
    ("bank_name",      False, "Bank name for commission payouts",                        None,                      "GTBank"),
    ("account_name",   False, "Account name",                                            None,                      "Tunde Ogundimu"),
    ("account_number", False, "10-digit bank account number",                            None,                      "0123456789"),
]

SALES_REP_SAMPLE_ROWS = [
    ["Tunde Ogundimu",   "tunde@email.com",   "+2348056789012", "STARTER", "TUNDE001", "GTBank",   "Tunde Ogundimu",   "0123456789"],
    ["Bola Fashola",     "bola@email.com",    "+2347065432198", "SENIOR",  "",         "Access",   "Bola Fashola",     "1234567890"],
    ["Ngozi Nwosu",      "ngozi@company.ng",  "+2349023456789", "LEGEND",  "NGOZI007", "Zenith",   "Ngozi Nwosu",      "9876543210"],
]


def _generate_referral_code(name: str, workspace):
    """Generate a unique referral code for a rep within the workspace."""
    from commissions.models import SalesRep
    base = "".join(c for c in name.upper().split()[0][:5] if c.isalpha())
    suffix = secrets.token_hex(2).upper()
    code = f"{base}{suffix}"
    # Ensure uniqueness
    while SalesRep.objects.filter(workspace=workspace, referral_code=code).exists():
        suffix = secrets.token_hex(2).upper()
        code = f"{base}{suffix}"
    return code


class SalesRepBulkUploadView(APIView):
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from commissions.models import SalesRep

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

        VALID_TIERS = {t.value for t in SalesRep.Tier}

        for idx, row in enumerate(rows, start=2):
            name  = row.get("name", "").strip()
            email = row.get("email", "").strip().lower()
            phone = row.get("phone", "").strip()

            if not name:
                errors.append({"row": idx, "error": "name is required"})
                continue
            if not email:
                errors.append({"row": idx, "error": "email is required"})
                continue
            if not phone:
                errors.append({"row": idx, "error": "phone is required"})
                continue
            if "@" not in email:
                errors.append({"row": idx, "error": f"invalid email '{email}'"})
                continue

            # Dedup by email within workspace
            if SalesRep.objects.filter(workspace=request.workspace, email__iexact=email).exists():
                skipped += 1
                continue

            raw_tier = row.get("tier", "").strip().upper()
            tier = raw_tier if raw_tier in VALID_TIERS else SalesRep.Tier.STARTER

            referral_code = row.get("referral_code", "").strip()
            if referral_code:
                # Ensure it's unique; if conflict skip with error
                if SalesRep.objects.filter(workspace=request.workspace, referral_code=referral_code).exists():
                    errors.append({"row": idx, "error": f"referral_code '{referral_code}' already exists"})
                    continue
            else:
                referral_code = _generate_referral_code(name, request.workspace)

            try:
                SalesRep.objects.create(
                    workspace=request.workspace,
                    name=name,
                    email=email,
                    phone=phone,
                    tier=tier,
                    referral_code=referral_code,
                    bank_name=row.get("bank_name", "").strip(),
                    bank_account_name=row.get("account_name", "").strip(),
                    bank_account_number=row.get("account_number", "").strip(),
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


class SalesRepBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return _simple_csv_response(
            SALES_REP_COLUMNS,
            SALES_REP_SAMPLE_ROWS,
            "terratrail_sales_reps_template.csv",
        )


# ===========================================================================
# Customer Reps
# ===========================================================================

CUSTOMER_REP_COLUMNS = [
    ("name",       True,  "Full name of the customer rep",                              None, "Amaka Okonkwo"),
    ("email",      True,  "Email address (unique per workspace, used for dedup)",       None, "amaka@email.com"),
    ("phone",      True,  "Phone number",                                               None, "+2348090123456"),
]

CUSTOMER_REP_SAMPLE_ROWS = [
    ["Amaka Okonkwo",  "amaka@email.com",  "+2348090123456"],
    ["Segun Adewale",  "segun@email.com",  "+2347011223344"],
    ["Ifeoma Chukwu",  "ifeoma@company.ng","+2349034567890"],
]


class CustomerRepBulkUploadView(APIView):
    """
    Creates workspace members with role CUSTOMER_REP.
    If the email already has a User account, that user is added to the workspace.
    If not, a new User with an unusable password is created.
    Existing members with the same email (any role) are skipped.
    """
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated, IsWorkspaceAdminOrReadOnly]

    def post(self, request):
        from accounts.models import User, WorkspaceMembership

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

        for idx, row in enumerate(rows, start=2):
            name  = row.get("name", "").strip()
            email = row.get("email", "").strip().lower()
            phone = row.get("phone", "").strip()

            if not name:
                errors.append({"row": idx, "error": "name is required"})
                continue
            if not email:
                errors.append({"row": idx, "error": "email is required"})
                continue
            if "@" not in email:
                errors.append({"row": idx, "error": f"invalid email '{email}'"})
                continue

            # Get or create the User
            try:
                user, user_created = User.objects.get_or_create(
                    email__iexact=email,
                    defaults={
                        "email": email,
                        "first_name": name.split()[0] if name else "",
                        "last_name": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
                        "phone": phone,
                    },
                )
                if user_created:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])
                elif phone and not user.phone:
                    user.phone = phone
                    user.save(update_fields=["phone"])
            except Exception as e:
                errors.append({"row": idx, "error": f"failed to create user: {e}"})
                continue

            # Check if already a member of this workspace
            if WorkspaceMembership.objects.filter(workspace=request.workspace, user=user).exists():
                skipped += 1
                continue

            try:
                WorkspaceMembership.objects.create(
                    workspace=request.workspace,
                    user=user,
                    role=WorkspaceMembership.Role.CUSTOMER_REP,
                    is_active=True,
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


class CustomerRepBulkTemplateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return _simple_csv_response(
            CUSTOMER_REP_COLUMNS,
            CUSTOMER_REP_SAMPLE_ROWS,
            "terratrail_customer_reps_template.csv",
        )
