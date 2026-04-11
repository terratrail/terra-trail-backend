from django.contrib import admin
from payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "transaction_reference", "installment", "amount",
        "status", "recorded_by", "approved_by", "payment_date",
    ]
    list_filter = ["status", "workspace"]
    search_fields = ["transaction_reference", "installment__subscription__customer__full_name"]
    readonly_fields = ["transaction_reference"]
