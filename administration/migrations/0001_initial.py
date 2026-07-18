# Generated manually for administration app

from django.db import migrations, models


def seed_initial_administration_users(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    AdministrationUser.objects.get_or_create(
        email="steliospatros@gmail.com",
        defaults={"is_active": True, "notes": "Initial administrator"},
    )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AdministrationUser",
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
                    "email",
                    models.EmailField(
                        help_text="Login email of a user who may open the administration panel.",
                        max_length=254,
                        unique=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Uncheck to revoke access without deleting the record.",
                    ),
                ),
                (
                    "notes",
                    models.CharField(
                        blank=True,
                        help_text="Optional note for internal use (e.g. role or name).",
                        max_length=255,
                    ),
                ),
                ("added_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Administration user",
                "verbose_name_plural": "Administration users",
                "ordering": ["email"],
            },
        ),
        migrations.RunPython(seed_initial_administration_users, migrations.RunPython.noop),
    ]
