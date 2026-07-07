from django.core.management.base import BaseCommand

from products.models import AnimalType, Category, Company


class Command(BaseCommand):
    """
    Populates the database with the initial 'lookup table' master data
    required for the shop to function: animal types, categories and
    companies (brands).

    This command is safe to run multiple times (idempotent): it uses
    get_or_create() so it will never create duplicate entries.

    Usage:
        python manage.py seed_data
    """
    help = "Seeds the database with initial AnimalType, Category and Company records."

    # Initial animal types supported by the shop.
    ANIMAL_TYPES = ["Dog", "Cat"]

    # Initial product categories supported by the shop.
    # Kept in Latin/English so all codebase content (including seed data)
    # stays ASCII-only; Greek translations for the storefront UI, if
    # needed, will be handled separately at the presentation layer (Part 5).
    CATEGORIES = ["Dry Food", "Canned Food", "Sachets", "Litter", "Bundle"]

    # Initial brands/companies, mapped to a short unique code each.
    # Codes are used internally (e.g. as a prefix for SKUs) and can be
    # edited later from the Django admin if needed.
    COMPANIES = {
        "Core": "COR",
        "CLUB4PAWS": "C4P",
        "OWNAT": "OWN",
        "PROFINE": "PRF",
        "EVERCLEAN": "EVC",
        "Wild Side": "WLD",
        "Puro Instinto": "PUR",
    }

    def handle(self, *args, **options):
        self._seed_animal_types()
        self._seed_categories()
        self._seed_companies()
        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully."))

    def _seed_animal_types(self):
        for name in self.ANIMAL_TYPES:
            obj, created = AnimalType.objects.get_or_create(name=name)
            self._report(obj, created, "AnimalType")

    def _seed_categories(self):
        for name in self.CATEGORIES:
            obj, created = Category.objects.get_or_create(name=name)
            self._report(obj, created, "Category")

    def _seed_companies(self):
        for name, code in self.COMPANIES.items():
            obj, created = Company.objects.get_or_create(
                name=name,
                defaults={"code": code},
            )
            self._report(obj, created, "Company")

    def _report(self, obj, created, label):
        # Print a clear line for every record, distinguishing new vs. existing.
        if created:
            self.stdout.write(self.style.SUCCESS(f"  + Created {label}: {obj}"))
        else:
            self.stdout.write(f"  = Already exists ({label}): {obj}")
