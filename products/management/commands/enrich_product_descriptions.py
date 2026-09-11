"""
Enrich short/empty product descriptions with professional Greek storefront copy.

Usage:
    python manage.py enrich_product_descriptions --dry-run
    python manage.py enrich_product_descriptions
    python manage.py enrich_product_descriptions --rewrite-generated
    python manage.py enrich_product_descriptions --force
"""
from django.core.management.base import BaseCommand

from products.description_copy import generate_product_description, needs_description_rewrite
from products.models import Product

# Phrases unique to products/description_copy.py — used to find prior AI rewrites.
GENERATED_MARKERS = (
    "υποστηρίζοντας ζωτικότητα, ευεξία και λαμπερό τρίχωμα",
    "κάνει κάθε γεύμα στιγμή φροντίδας",
    "συνδυάζει υψηλή πεπτικότητα με γεύση που αγαπούν",
    "σέβονται τις πραγματικές ανάγκες του κατοικίδιου σας",
    "δελεάζει ακόμη και τους πιο απαιτητικούς ουρανίσκους",
    "χωρίς συμβιβασμούς στην ποιότητα",
    "υγρή, πλούσια σε κρέας υφή",
    "καθαρές, υψηλής διατροφικής αξίας συνθέσεις",
)


def _looks_generated(text: str) -> bool:
    return any(marker in text for marker in GENERATED_MARKERS)


class Command(BaseCommand):
    help = "Rewrite short product descriptions into professional Greek marketing copy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-len",
            type=int,
            default=120,
            help="Update products whose current description length is below this (default: 120).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rewrite all products, not only short ones.",
        )
        parser.add_argument(
            "--rewrite-generated",
            action="store_true",
            help="Rewrite products previously filled by this command (grammar refresh).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )

    def handle(self, *args, **options):
        max_len = options["max_len"]
        force = options["force"]
        rewrite_generated = options["rewrite_generated"]
        dry_run = options["dry_run"]

        qs = Product.objects.select_related("company", "animal_type", "category").order_by("id")
        updated = 0
        skipped = 0

        for product in qs:
            current = (product.description or "").strip()
            is_generated = _looks_generated(current)
            poor = needs_description_rewrite(current)
            if not force and not rewrite_generated and not poor and len(current) >= max_len:
                skipped += 1
                continue
            if rewrite_generated and not force and not is_generated and not poor and len(current) >= max_len:
                skipped += 1
                continue

            # Do not re-embed previous AI copy as a "seed" tagline.
            seed = "" if is_generated else current

            new_text = generate_product_description(
                name=product.name,
                company=product.company.name,
                animal=product.animal_type.name,
                category=product.category.name,
                seed_description=seed,
                bundle_contents=product.bundle_contents or "",
            )

            if dry_run:
                self.stdout.write(f"[DRY RUN] #{product.pk} {product.company.name} — {product.name}")
                self.stdout.write(f"  OLD ({len(current)}): {current[:140]!r}")
                self.stdout.write(f"  NEW ({len(new_text)}): {new_text}")
                self.stdout.write("")
            else:
                product.description = new_text
                product.save(update_fields=["description", "updated_at"])

            updated += 1

        action = "Would update" if dry_run else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} {updated} product(s); skipped {skipped}.")
        )
