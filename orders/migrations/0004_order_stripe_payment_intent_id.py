# Generated manually for Stripe PaymentIntent linkage.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0003_alter_order_cart_cost_alter_order_delivery_address_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="stripe_payment_intent_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Stripe PaymentIntent ID for card payments (pi_...). Empty for cash on delivery.",
                max_length=255,
            ),
        ),
    ]
