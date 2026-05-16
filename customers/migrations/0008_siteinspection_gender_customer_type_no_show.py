"""
Migration: SiteInspection — add gender, customer_type fields; add NO_SHOW to status.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0007_add_attendees_to_siteinspection"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteinspection",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[
                    ("MALE", "Male"),
                    ("FEMALE", "Female"),
                    ("PREFER_NOT_TO_SAY", "Prefer not to say"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="siteinspection",
            name="customer_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("EXISTING", "Existing Customer"),
                    ("NEW", "New Customer"),
                ],
                default="",
                help_text="Auto-set on creation: EXISTING if email matches a customer, else NEW.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="siteinspection",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("ATTENDED", "Attended"),
                    ("CANCELLED", "Cancelled"),
                    ("NO_SHOW", "No Show"),
                ],
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
