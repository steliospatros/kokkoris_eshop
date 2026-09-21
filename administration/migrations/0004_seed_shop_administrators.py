from django.db import migrations

ADMIN_EMAILS = (
    ("kokkorisofficial@gmail.com", "Brand Gmail — shop administrator"),
    ("steliospatros@gmail.com", "Shop administrator"),
    ("prolamprou@gmail.com", "Shop administrator"),
)


def seed_shop_administrators(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    for email, notes in ADMIN_EMAILS:
        record, created = AdministrationUser.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "role": "admin",
                "notes": notes,
            },
        )
        if not created:
            record.is_active = True
            record.role = "admin"
            if not record.notes:
                record.notes = notes
            record.save(update_fields=["is_active", "role", "notes"])


def unseed_shop_administrators(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    AdministrationUser.objects.filter(
        email="prolamprou@gmail.com",
        notes="Shop administrator",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administration", "0003_administrationuser_kokkorisofficial"),
    ]

    operations = [
        migrations.RunPython(seed_shop_administrators, unseed_shop_administrators),
    ]
