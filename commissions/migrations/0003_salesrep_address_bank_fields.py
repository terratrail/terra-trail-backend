from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commissions", "0002_rename_tiers_starter_senior_legend"),
    ]

    operations = [
        migrations.AddField(
            model_name="salesrep",
            name="address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="salesrep",
            name="bank_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="salesrep",
            name="bank_account_number",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="salesrep",
            name="bank_account_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
