from django.contrib import admin
from accounts.models import User, WorkspaceMembership, OTPToken


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "first_name", "last_name", "default_role", "is_active", "date_joined"]
    list_filter = ["default_role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-date_joined"]


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
