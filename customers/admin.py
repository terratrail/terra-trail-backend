from django.contrib import admin
from customers.models import Customer, Installment, Subscription


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "phone", "workspace", "referral_source", "created_at"]
    list_filter = ["referral_source", "workspace"]
    search_fields = ["full_name", "email", "phone"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "customer", "property", "pricing_plan",
        "total_price", "amount_paid", "balance",
        "status", "start_date", "estimated_end_date",
    ]
    list_filter = ["status", "workspace"]
    search_fields = ["customer__full_name", "property__name"]


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = [
        "subscription", "installment_number", "due_date",
        "amount", "status", "paid_date",
    ]
    list_filter = ["status"]
    search_fields = ["subscription__customer__full_name"]
