from django.db import migrations, models


def collapse_legacy_statuses(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.filter(status__in=("pending", "paid")).update(status="new")
    Order.objects.filter(status="failed").update(status="cancelled")


def noop_reverse(apps, schema_editor):
    """Legacy payment statuses are not restored; payment lives on Stripe fields."""


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0012_order_cancellation_reason"),
    ]

    operations = [
        migrations.RunPython(collapse_legacy_statuses, noop_reverse),
        migrations.AlterField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("new", "Registered"),
                    ("delivered", "Delivered"),
                    ("cancelled", "Cancelled"),
                    ("cancel_req", "Cancellation requested"),
                ],
                default="new",
                help_text=(
                    "Fulfillment only: registered, delivered, cancellation "
                    "requested, or cancelled. Payment is tracked separately."
                ),
                max_length=10,
            ),
        ),
    ]
