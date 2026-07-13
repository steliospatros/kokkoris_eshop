from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_customuser_floor_customuser_latitude_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="doorbell_name",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Name on the doorbell / intercom at delivery address.",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="customuser",
            name="floor",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Delivery floor (preset or custom). Filled in during checkout.",
                max_length=50,
            ),
        ),
    ]
