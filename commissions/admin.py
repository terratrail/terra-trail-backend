from django.contrib import admin
from commissions.models import Commission, SalesRep


@admin.register(SalesRep)
class SalesRepAdmin(admin.ModelAdmin):
    list_display = [
        "name", "email", "tier", "referral_code",
        "commission_type", "commission_rate", "is_active",
    ]
    list_filter = ["tier", "is_active", "workspace"]
    search_fields = ["name", "email", "referral_code"]


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = [
        "sales_rep", "payment", "amount", "status", "paid_date",
    ]
    list_filter = ["status", "workspace"]
    search_fields = ["sales_rep__name"]
