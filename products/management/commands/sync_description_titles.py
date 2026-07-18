"""Sync embedded titles inside product descriptions with current Product.name."""
from django.core.management.base import BaseCommand

from products.description_sync import sync_description_title
from products.models import Product


class Command(BaseCommand):
    help = (
        "Update Product.description so quoted titles match Product.name "
        "and «φυλή/φυλών» become «ράτσα/ρατσών»."
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

        for product in Product.objects.order_by("id"):
            new_desc = sync_description_title(product.description or "", product.name)
            if new_desc == (product.description or ""):
                continue

            self.stdout.write(f"  [{product.id}] {product.name[:60]}")
            # Show only the changed opening when possible
            old_head = (product.description or "")[:100].replace("\n", " ")
            new_head = new_desc[:100].replace("\n", " ")
            self.stdout.write(f"    was: {old_head}…")
            self.stdout.write(f"    now: {new_head}…")

            if not dry_run:
                product.description = new_desc
                product.save(update_fields=["description", "updated_at"])
            updated += 1

        suffix = "would update" if dry_run else "updated"
        self.stdout.write(self.style.SUCCESS(f"{suffix}: {updated} description(s)"))
