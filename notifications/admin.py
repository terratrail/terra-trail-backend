from django.contrib import admin
from notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        "notification_type", "recipient", "subject",
        "status", "sent_at", "created_at",
    ]
    list_filter = ["notification_type", "status", "workspace"]
    search_fields = ["recipient", "subject"]
    readonly_fields = ["sent_at"]
