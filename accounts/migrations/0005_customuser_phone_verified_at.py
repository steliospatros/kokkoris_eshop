from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_customuser_area_customuser_street_customuser_street_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="phone_verified_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="When the mobile number was confirmed via SMS OTP.",
            ),
        ),
    ]
