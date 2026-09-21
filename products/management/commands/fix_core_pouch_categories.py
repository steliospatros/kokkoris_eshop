"""Move Core pouch SKUs from Canned Food into Sachets."""
from django.core.management.base import BaseCommand

from products.description_copy import generate_product_description
from products.description_sync import sync_description_title
from products.management.commands.import_core import classify_core_wet_category
from products.models import Category, Product, ProductVariant
from products.name_i18n import translate_product_name_to_greek


class Command(BaseCommand):
    help = (
        "Reclassify Wellness CORE Tender Cuts (78863*) and Purely Paté (78865*) "
        "pouches from Canned Food to Sachets, then refresh Greek titles/copy."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        sachets = Category.objects.get(slug="sachets")
        canned = Category.objects.get(slug="canned-food")

        variants = ProductVariant.objects.filter(
            product__company__name="Core",
            product__category=canned,
        ).select_related("product", "product__animal_type", "product__company")

        moved_ids = []
        for variant in variants:
            if classify_core_wet_category(variant.sku or "") != "Sachets":
                continue
            product = variant.product
            if product.id in moved_ids:
                continue
            moved_ids.append(product.id)
            old_name = product.name
            new_name = translate_product_name_to_greek(
                old_name,
                animal_slug=product.animal_type.slug,
                slug=product.slug,
                category_slug="sachets",
            )
            new_name = new_name.replace("κονσέρβα", "φάκελος")
            new_desc = generate_product_description(
                name=new_name,
                company=product.company.name,
                animal=product.animal_type.name,
                category="Sachets",
                seed_description="",
                bundle_contents=product.bundle_contents or "",
            )
            new_desc = sync_description_title(new_desc, new_name)
            self.stdout.write(f"  {old_name}\n    → {new_name}  [{variant.sku}]")
            if dry_run:
                continue
            product.category = sachets
            product.name = new_name
            product.description = new_desc
            product.save(update_fields=["category", "name", "description", "updated_at"])

        suffix = "would move" if dry_run else "moved"
        self.stdout.write(self.style.SUCCESS(f"{suffix}: {len(moved_ids)} product(s)"))
