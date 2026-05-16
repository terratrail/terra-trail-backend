"""
Migration: InspectionConfig OneToOneField → ForeignKey, add new fields;
           Property.assigned_customer_rep FK.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0009_add_estate_land_title_brochure"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Step 1: rename the old OneToOneField column so we can recreate it ──
        # Django stores FK and O2O columns with the same naming convention (_id
        # suffix), so we need to: drop the unique constraint (implied by O2O),
        # then alter the field type.  The cleanest approach is to use
        # AlterField which handles both the constraint and column in one go
        # (SQLite-safe).
        migrations.AlterField(
            model_name="inspectionconfig",
            name="property",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="inspection_configs",
                to="properties.property",
            ),
        ),

        # ── Step 2: add new InspectionConfig fields ──────────────────────────
        migrations.AddField(
            model_name="inspectionconfig",
            name="schedule_mode",
            field=models.CharField(
                choices=[("RECURRING", "Recurring"), ("ONE_TIME", "One-Time")],
                default="RECURRING",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="inspectionconfig",
            name="tag",
            field=models.CharField(
                blank=True,
                default="",
                help_text="e.g. VIP, Group Tour, Standard",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="inspectionconfig",
            name="end_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="For RECURRING configs — when the schedule stops.",
            ),
        ),
        migrations.AddField(
            model_name="inspectionconfig",
            name="inspection_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="For ONE_TIME configs — the specific inspection date.",
            ),
        ),
        migrations.AddField(
            model_name="inspectionconfig",
            name="inspection_time",
            field=models.TimeField(
                blank=True,
                null=True,
                help_text="For ONE_TIME configs — the specific inspection time.",
            ),
        ),
        migrations.AddField(
            model_name="inspectionconfig",
            name="additional_notes",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Internal notes field",
            ),
        ),

        # ── Step 3: add Property.assigned_customer_rep ───────────────────────
        migrations.AddField(
            model_name="property",
            name="assigned_customer_rep",
            field=models.ForeignKey(
                blank=True,
                help_text="Customer-facing representative assigned to this property.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_properties",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
