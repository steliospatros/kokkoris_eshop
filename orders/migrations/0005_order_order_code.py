import secrets
import string

from django.db import migrations, models


def populate_order_codes(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    alphabet = string.ascii_uppercase + string.digits
    used = set(
        Order.objects.exclude(order_code="").values_list("order_code", flat=True)
    )

    for order in Order.objects.filter(order_code=""):
        while True:
            candidate = "KPK" + "".join(
                secrets.choice(alphabet) for _ in range(8)
            )
            if candidate not in used:
                used.add(candidate)
                order.order_code = candidate
                order.save(update_fields=["order_code"])
                break


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_order_stripe_payment_intent_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="order_code",
            field=models.CharField(
                max_length=16,
                blank=True,
                default="",
                help_text="Public order identifier shown to customers, e.g. KPK4F8A2B1C.",
            ),
        ),
        migrations.RunPython(populate_order_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="order",
            name="order_code",
            field=models.CharField(
                max_length=16,
                unique=True,
                help_text="Public order identifier shown to customers, e.g. KPK4F8A2B1C.",
            ),
        ),
    ]
