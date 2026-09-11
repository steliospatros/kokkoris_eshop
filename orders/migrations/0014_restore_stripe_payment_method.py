"""
Repair orders whose payment method was overwritten by the admin panel.

The old `mark_order_paid` wrote both `payment_method` and
`collected_payment_method`, so declaring a cash collection on an order that
had already been paid online turned it into an αντικαταβολή — and the payments
dashboard then listed the money as still expected. Only card checkout ever
stores a PaymentIntent, so its presence is enough to restore the method.
"""
from django.db import migrations


def restore_card_payment_method(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    paid_online = Order.objects.exclude(stripe_payment_intent_id="")
    paid_online.exclude(payment_method="card").update(payment_method="card")
    # Prepaid orders collect nothing at the door until they are handed over.
    paid_online.exclude(status="delivered").exclude(
        collected_payment_method=""
    ).update(collected_payment_method="")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0013_collapse_order_statuses"),
    ]

    operations = [
        migrations.RunPython(restore_card_payment_method, migrations.RunPython.noop),
    ]
