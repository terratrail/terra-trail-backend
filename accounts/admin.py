from django.contrib import admin
from accounts.models import User, WorkspaceMembership, OTPToken


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "full_name", "phone", "default_role", "is_active", "date_joined"]
    list_filter = ["default_role", "is_active", "gender", "marital_status"]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("title", "first_name", "last_name", "phone", "gender", "date_of_birth")}),
        ("Professional Info", {"fields": ("occupation", "marital_status")}),
        ("Location", {"fields": ("address", "country", "state", "nationality")}),
        ("Permissions", {"fields": ("default_role", "is_active", "is_staff", "is_superuser")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(WorkspaceMembership)
class WorkspaceMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "workspace", "role", "is_active", "created_at"]
    list_filter = ["role", "is_active"]
    search_fields = ["user__email", "workspace__name"]


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ["email", "code", "attempts", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["email"]
