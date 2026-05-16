"""
Migration: Installment — add amount_paid field; add PARTIALLY_PAID to status choices.
"""

from decimal import Decimal
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0008_siteinspection_gender_customer_type_no_show"),
    ]

    operations = [
        migrations.AddField(
            model_name="installment",
            name="amount_paid",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Tracks how much has been paid toward this installment so far.",
                max_digits=14,
            ),
        ),
        migrations.AlterField(
            model_name="installment",
            name="status",
            field=models.CharField(
                choices=[
                    ("UPCOMING", "Upcoming"),
                    ("DUE", "Due"),
                    ("OVERDUE", "Overdue"),
                    ("PENDING", "Pending"),
                    ("PARTIALLY_PAID", "Partially Paid"),
                    ("PAID", "Paid"),
                ],
                default="UPCOMING",
                max_length=20,
            ),
        ),
    ]
