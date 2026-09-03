from decimal import ROUND_CEILING, Decimal

from django.db import migrations

CENT = Decimal("0.01")
TENTH = Decimal("0.1")


def ceil_to_tenth(value):
    amount = Decimal(value)
    if amount <= 0:
        return Decimal("0.00")
    return amount.quantize(TENTH, rounding=ROUND_CEILING).quantize(CENT)


def ceil_prices(apps, schema_editor):
    Variant = apps.get_model("products", "ProductVariant")
    for variant in Variant.objects.iterator():
        rounded = ceil_to_tenth(variant.price)
        if rounded != variant.price:
            Variant.objects.filter(pk=variant.pk).update(price=rounded)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0006_favourite"),
    ]

    operations = [
        migrations.RunPython(ceil_prices, noop),
    ]
