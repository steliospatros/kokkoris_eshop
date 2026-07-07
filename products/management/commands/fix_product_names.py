from django.core.management.base import BaseCommand

from products.management.commands.import_club4paws import fix_greek_accents
from products.models import Product


class Command(BaseCommand):
    help = (
        "Normalise Greek accents in existing Product.name values "
        "(idempotent — safe to re-run)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print changes without saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated = 0

        for product in Product.objects.select_related("company").iterator():
            fixed = fix_greek_accents(product.name)
            if fixed != product.name:
                self.stdout.write(f"  {product.name!r} -> {fixed!r}")
                if not dry_run:
                    product.name = fixed
                    product.save(update_fields=["name"])
                updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(f"Dry run: {updated} product(s) would change."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Updated {updated} product name(s)."))
