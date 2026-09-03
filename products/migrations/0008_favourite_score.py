from django.db import migrations, models
from django.db.models import F


def seed_score_from_purchases(apps, schema_editor):
    Favourite = apps.get_model("products", "Favourite")
    Favourite.objects.update(score=F("purchase_count") * 5)


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0007_ceil_variant_prices_to_tenth"),
    ]

    operations = [
        migrations.AddField(
            model_name="favourite",
            name="score",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Dynamic popularity score (sale +5, wishlist +3, view +1).",
            ),
        ),
        migrations.AddField(
            model_name="favourite",
            name="wishlist_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Times this product was added to a wishlist.",
            ),
        ),
        migrations.AddField(
            model_name="favourite",
            name="view_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Unique session views of the product page.",
            ),
        ),
        migrations.AlterField(
            model_name="favourite",
            name="purchase_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Total units sold across all variants.",
            ),
        ),
        migrations.AlterModelOptions(
            name="favourite",
            options={
                "ordering": ["-score", "-purchase_count", "product__name"],
                "verbose_name": "Favourite",
                "verbose_name_plural": "Favourites",
            },
        ),
        migrations.RunPython(seed_score_from_purchases, migrations.RunPython.noop),
    ]
