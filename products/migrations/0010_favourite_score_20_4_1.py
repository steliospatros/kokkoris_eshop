from django.db import migrations, models
from django.db.models import F


def rescore_favourites(apps, schema_editor):
    Favourite = apps.get_model("products", "Favourite")
    Favourite.objects.update(
        score=F("purchase_count") * 20 + F("wishlist_count") * 4 + F("view_count") * 1
    )


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0009_favourite_view"),
    ]

    operations = [
        migrations.AlterField(
            model_name="favourite",
            name="score",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Dynamic popularity score (sale +20, wishlist +4, view +1 once per user).",
            ),
        ),
        migrations.RunPython(rescore_favourites, migrations.RunPython.noop),
    ]
