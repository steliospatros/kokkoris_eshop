from django.db import migrations


def seed_brand_administrator(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    AdministrationUser.objects.get_or_create(
        email="kokkorisofficial@gmail.com",
        defaults={
            "is_active": True,
            "role": "admin",
            "notes": "Brand Gmail — shop administrator and transactional sender",
        },
    )


def unseed_brand_administrator(apps, schema_editor):
    AdministrationUser = apps.get_model("administration", "AdministrationUser")
    AdministrationUser.objects.filter(email="kokkorisofficial@gmail.com").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administration", "0002_administrationuser_role"),
    ]

    operations = [
        migrations.RunPython(seed_brand_administrator, unseed_brand_administrator),
    ]
