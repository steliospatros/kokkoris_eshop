# Generated manually for cancellation/refund workflow fields.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_order_order_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="cancellation_requested_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When the customer submitted a cancellation/refund request.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="stripe_refund_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Stripe Refund ID (re_...) after admin processes a card refund.",
                max_length=255,
            ),
        ),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "New"),
                    ("pending", "Pending"),
                    ("paid", "Paid"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                    ("failed", "Failed"),
                    ("cancel_req", "Cancellation requested"),
                ],
                default="new",
                help_text="Where this order currently stands in the payment/delivery lifecycle.",
                max_length=10,
            ),
        ),
    ]
