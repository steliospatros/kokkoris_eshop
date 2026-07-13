from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_customuser_doorbell_name_alter_customuser_floor"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="area",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Neighborhood / suburb (e.g. Χαλανδρί when city is Αθήνα).",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="street",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Street name (route) from parsed delivery address.",
                max_length=150,
            ),
        ),
        migrations.AddField(
            model_name="customuser",
            name="street_number",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Street number from parsed delivery address.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="address",
            field=models.CharField(
                blank=True,
                help_text="Legacy single-line address (street + number). Kept for checkout compat.",
                max_length=255,
            ),
        ),
    ]
