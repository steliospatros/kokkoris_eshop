from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_collected_payment_and_delivered_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="cancellation_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Reason written by staff when cancelling. Shown to the customer.",
            ),
        ),
    ]
