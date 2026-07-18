"""Rewrite product titles into subject-first meaning-based Greek."""
from django.core.management.base import BaseCommand

from products.description_sync import sync_description_title
from products.models import Product
from products.name_i18n import needs_greek_translation, translate_product_name_to_greek


class Command(BaseCommand):
    help = (
        "Build subject-first Greek Product.name values "
        "(flavor/category - για audience). Also syncs quoted titles in descriptions. "
        "Slugs/URLs unchanged. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print proposed renames without saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        updated_names = 0
        updated_descs = 0
        remaining = 0

        qs = Product.objects.select_related(
            "company", "animal_type", "category"
        ).order_by("id")
        for product in qs:
            old_name = product.name
            old_desc = product.description or ""

            new_name = translate_product_name_to_greek(
                old_name,
                animal_slug=product.animal_type.slug,
                slug=product.slug,
                category_slug=product.category.slug,
            )
            new_desc = sync_description_title(old_desc, new_name)

            if new_name != old_name:
                self.stdout.write(f"  {old_name!r}\n    → {new_name!r}")
                updated_names += 1
            elif needs_greek_translation(old_name):
                remaining += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  still awkward: [{product.company.name}] {old_name}"
                    )
                )

            if new_desc != old_desc:
                if new_name == old_name:
                    self.stdout.write(f"  desc sync: {new_name[:60]}")
                updated_descs += 1

            if dry_run or (new_name == old_name and new_desc == old_desc):
                continue

            product.name = new_name
            product.description = new_desc
            update_fields = ["updated_at"]
            if new_name != old_name:
                update_fields.insert(0, "name")
            if new_desc != old_desc:
                update_fields.insert(0, "description")
            product.save(update_fields=update_fields)

        suffix = "would update" if dry_run else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{suffix}: {updated_names} name(s), {updated_descs} description(s); "
                f"still needing review: {remaining}"
            )
        )
