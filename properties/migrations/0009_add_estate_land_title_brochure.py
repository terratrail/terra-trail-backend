from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("properties", "0008_add_inspection_slots"),
    ]

    operations = [
        migrations.AddField(
            model_name="property",
            name="estate_land_title",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Title/deed reference number for the estate land.",
                max_length=255,
            ),
        ),
        migrations.AddField(
            model_name="property",
            name="brochure",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to="properties/brochures/",
                help_text="PDF brochure for the property.",
            ),
        ),
    ]
