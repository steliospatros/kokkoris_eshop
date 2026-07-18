import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Sum


def backfill_favourites(apps, schema_editor):
    Favourite = apps.get_model("products", "Favourite")
    Product = apps.get_model("products", "Product")
    OrderItem = apps.get_model("orders", "OrderItem")

    counts = {}
    for row in (
        OrderItem.objects.values("product_variant__product_id")
        .annotate(total=Sum("quantity"))
    ):
        product_id = row["product_variant__product_id"]
        if product_id:
            counts[product_id] = row["total"] or 0

    favourites = [
        Favourite(
            product_id=product.pk,
            purchase_count=counts.get(product.pk, 0),
        )
        for product in Product.objects.all()
    ]
    Favourite.objects.bulk_create(favourites)


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
        ("products", "0005_product_shipping_dimensions"),
    ]

    operations = [
        migrations.CreateModel(
            name="Favourite",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "purchase_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total units sold across all variants; higher = more popular.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="favourite",
                        to="products.product",
                    ),
                ),
            ],
            options={
                "verbose_name": "Favourite",
                "verbose_name_plural": "Favourites",
                "db_table": "favourites",
                "ordering": ["-purchase_count", "product__name"],
            },
        ),
        migrations.RunPython(backfill_favourites, migrations.RunPython.noop),
    ]
