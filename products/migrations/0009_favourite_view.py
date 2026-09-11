from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("products", "0008_favourite_score"),
    ]

    operations = [
        migrations.CreateModel(
            name="FavouriteView",
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
                ("visitor_key", models.CharField(db_index=True, max_length=32)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="score_views",
                        to="products.product",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_score_views",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Favourite view",
                "verbose_name_plural": "Favourite views",
            },
        ),
        migrations.AddConstraint(
            model_name="favouriteview",
            constraint=models.UniqueConstraint(
                condition=models.Q(("user__isnull", False)),
                fields=("product", "user"),
                name="unique_favourite_view_per_user",
            ),
        ),
        migrations.AddConstraint(
            model_name="favouriteview",
            constraint=models.UniqueConstraint(
                fields=("product", "visitor_key"),
                name="unique_favourite_view_per_visitor",
            ),
        ),
        migrations.AlterField(
            model_name="favourite",
            name="view_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Unique visitors who opened the product page (once per user).",
            ),
        ),
    ]
