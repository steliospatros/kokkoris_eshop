from django.db import migrations

EMAIL = "labroukalli@gmail.com"
NOTES = "Shop administrator — Καλλή"


def seed_labroukalli_admin(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    record, created = AdministrationUser.objects.get_or_create(
        email=EMAIL,
        defaults={
            "is_active": True,
            "role": "admin",
            "notes": NOTES,
        },
    )
    if not created:
        record.is_active = True
        record.role = "admin"
        if not record.notes:
            record.notes = NOTES
        record.save(update_fields=["is_active", "role", "notes"])


def unseed_labroukalli_admin(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    AdministrationUser.objects.filter(email=EMAIL, notes=NOTES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administration", "0004_seed_shop_administrators"),
    ]

    operations = [
        migrations.RunPython(seed_labroukalli_admin, unseed_labroukalli_admin),
    ]
