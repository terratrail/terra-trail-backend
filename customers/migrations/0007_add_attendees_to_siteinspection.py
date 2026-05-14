from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0006_add_plot_allocation_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="siteinspection",
            name="attendees",
            field=models.JSONField(blank=True, default=list, help_text='List of attendees: [{"name": "...", "phone": "...", "email": "..."}]'),
        ),
    ]
