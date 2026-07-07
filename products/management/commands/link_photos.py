"""
Links product photos to existing Product records in the database.

The client provides photos grouped in per-animal folders (e.g. "DOGS PHOTO",
"CATS PHOTO"), where each filename is essentially the same life-stage/flavor
header text used in the original catalogue document (e.g.
"ADULT SMALL BREEDS ΜΕ ΚΟΤΟΠΟΥΛΟ.png"). This command reuses the exact same
text-cleaning helpers from `import_club4paws` to rebuild a product name from
each filename, then looks up the matching Product and attaches the photo to
its `image` field.

Matching strategy, in order:
    1. Exact SKU match (for Bundle/multipack photos named after their SKU,
       e.g. "86C210Μ.png").
    2. Exact product name match, after normalizing minor filename quirks
       (e.g. "MEDIUM_LARGE" -> "Medium/Large", stray "ζελέ" without a
       leading "σε").
    3. Fuzzy match: if the plain flavor doesn't exist, try appending
       " in Gravy" / " in Jelly" (covers photos whose filename omits the
       sauce/jelly suffix that exists on the matching Sachets product).
    4. Best-effort "generic" match: a photo with no flavor at all (e.g.
       "ADULT ALL BREEDS.png") is assigned to the single remaining
       still-photo-less product that shares its life-stage, if exactly one
       such candidate remains once every other photo has been processed.

A product that already has a photo assigned during this run is never
overwritten by a second candidate file (first match wins); such files are
reported as skipped duplicates for manual review.

Usage:
    python manage.py link_photos --base-dir "/path/to/folder" --dry-run
    python manage.py link_photos --base-dir "/path/to/folder"

The --base-dir must contain one subfolder per animal type, with "dog" or
"cat" appearing anywhere in the subfolder name (case-insensitive), e.g.
"DOGS PHOTO" / "CATS PHOTO".
"""
import os
import re

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from products.management.commands.import_club4paws import (
    clean_flavor,
    clean_life_stage,
    split_header_line,
)
from products.models import Product, ProductVariant

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def normalize_filename_quirks(name):
    """Fixes small, known inconsistencies between photo filenames and the
    text patterns produced by the catalogue parser."""
    name = name.replace("_", "/")
    # A trailing "ζελέ"/"σάλτσα" with no "σε" in front is still meant as the
    # jelly/gravy suffix (e.g. "... ΠΑΠΙΑ ζελέ.png").
    name = re.sub(r'(?<!σε )(?<!ΣΕ )ζελέ\b', 'σε ζελέ', name, flags=re.IGNORECASE)
    name = re.sub(r'(?<!σε )(?<!ΣΕ )σάλτσα\b', 'σε σάλτσα', name, flags=re.IGNORECASE)
    # A trailing package-size hint like "100GR"/"85 GR" (e.g. distinguishing
    # a small sachet-size photo from the main dry-food bag photo) isn't part
    # of the product name itself - drop it so the flavor still matches.
    name = re.sub(r'\s*\d+\s*GR\b', '', name, flags=re.IGNORECASE)
    return name


def build_name_from_text(raw):
    life_part, flavor_part = split_header_line(raw)
    life_stage = clean_life_stage(life_part)
    flavor = clean_flavor(flavor_part) if flavor_part else ""
    parts = [p for p in (life_stage, flavor) if p]
    return " - ".join(parts) if parts else None


class Command(BaseCommand):
    help = "Attaches photo files to existing Products by matching filenames to product names/SKUs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-dir", required=True,
            help='Folder containing per-animal photo subfolders (e.g. "DOGS PHOTO", "CATS PHOTO").',
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would be matched/linked without copying any files or touching the database.",
        )

    def handle(self, *args, **options):
        base_dir = options["base_dir"]
        dry_run = options["dry_run"]

        if not os.path.isdir(base_dir):
            raise CommandError(f"Folder not found: {base_dir}")

        animal_folders = self._discover_animal_folders(base_dir)
        if not animal_folders:
            raise CommandError(
                "No subfolders with 'dog' or 'cat' in their name were found under --base-dir."
            )

        variant_by_sku = {
            v.sku: v for v in ProductVariant.objects.exclude(sku__isnull=True).exclude(sku="")
        }
        products_by_key = {}
        for p in Product.objects.select_related("animal_type"):
            products_by_key.setdefault((p.animal_type.name, p.name), p)

        claimed_product_ids = set(
            Product.objects.exclude(image="").values_list("id", flat=True)
        )

        assignments = []       # (photo_path, product, note)
        skipped_duplicate = []  # (photo_path, product)
        unmatched = []          # (photo_path, animal, built_name)

        for animal, folder_path in animal_folders.items():
            for fname in sorted(os.listdir(folder_path)):
                stem, ext = os.path.splitext(fname)
                if ext.lower() not in IMAGE_EXTENSIONS:
                    continue
                photo_path = os.path.join(folder_path, fname)
                stem = stem.strip()

                # 1. Direct SKU match (bundle/multipack photos).
                if stem in variant_by_sku:
                    product = variant_by_sku[stem].product
                    self._add_assignment(
                        product, photo_path, "SKU match", assignments,
                        skipped_duplicate, claimed_product_ids,
                    )
                    continue

                # 2 & 3. Exact name match and fuzzy (sauce/jelly suffix) match.
                # A filename carrying an explicit small gram size (e.g. "100GR")
                # almost always identifies a Sachets pouch photo rather than
                # the dry-food bag, so for those we try the sauce/jelly
                # variants *before* the plain exact name.
                normalized = normalize_filename_quirks(stem)
                built_name = build_name_from_text(normalized)
                has_gram_hint = bool(re.search(r'\d+\s*GR\b', stem, re.IGNORECASE))

                candidate_names = []
                if built_name:
                    if has_gram_hint:
                        candidate_names = [built_name + " in Gravy", built_name + " in Jelly", built_name]
                    else:
                        candidate_names = [built_name, built_name + " in Gravy", built_name + " in Jelly"]

                found = [
                    (name, products_by_key[(animal, name)])
                    for name in candidate_names
                    if (animal, name) in products_by_key
                ]
                # Prefer the first candidate that is not already claimed by
                # another photo; otherwise fall back to the first match found
                # (which will be reported as a duplicate below).
                unclaimed = [(n, p) for n, p in found if p.id not in claimed_product_ids]
                matched_name, product = (unclaimed or found)[0] if found else (None, None)

                if product:
                    note = "name match" if matched_name == built_name else f"fuzzy match (assumed '{built_name}...')"
                    self._add_assignment(
                        product, photo_path, note, assignments,
                        skipped_duplicate, claimed_product_ids,
                    )
                    continue

                unmatched.append((photo_path, animal, built_name))

        # 4. Best-effort pass for generic, flavor-less photos (e.g. "ADULT ALL BREEDS.png"):
        # assign to the single remaining photo-less product sharing that life-stage, if unambiguous.
        still_unmatched = []
        for photo_path, animal, built_name in unmatched:
            if not built_name:
                still_unmatched.append((photo_path, animal, built_name))
                continue
            candidates = [
                p for (a, name), p in products_by_key.items()
                if a == animal and name.startswith(built_name) and p.id not in claimed_product_ids
            ]
            if len(candidates) == 1:
                self._add_assignment(
                    candidates[0], photo_path, f"best-effort guess (generic '{built_name}' photo)",
                    assignments, skipped_duplicate, claimed_product_ids,
                )
            else:
                still_unmatched.append((photo_path, animal, built_name))

        # --- Report -----------------------------------------------------
        self.stdout.write(self.style.SUCCESS(f"\nWould link {len(assignments)} photos:" if dry_run else f"\nLinking {len(assignments)} photos:"))
        for photo_path, product, note in assignments:
            self.stdout.write(f"  {os.path.basename(photo_path):55} -> {product.name}  [{note}]")

        if skipped_duplicate:
            self.stdout.write(self.style.WARNING(f"\nSkipped {len(skipped_duplicate)} duplicate/alternate photos (product already has an image):"))
            for photo_path, product in skipped_duplicate:
                self.stdout.write(f"  {os.path.basename(photo_path)} -> {product.name} (already has a photo)")

        if still_unmatched:
            self.stdout.write(self.style.WARNING(f"\n{len(still_unmatched)} photos could not be matched to any product:"))
            for photo_path, animal, built_name in still_unmatched:
                self.stdout.write(f"  {os.path.basename(photo_path)} (animal={animal}, attempted name={built_name!r})")

        photoless = Product.objects.exclude(id__in=claimed_product_ids)
        if not dry_run:
            # Recompute after actually saving below.
            pass

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - no files were copied and no database changes were made."))
            return

        # --- Apply --------------------------------------------------------
        linked_count = 0
        for photo_path, product, note in assignments:
            with open(photo_path, "rb") as f:
                django_file = File(f)
                product.image.save(os.path.basename(photo_path), django_file, save=True)
            linked_count += 1

        remaining_photoless = Product.objects.filter(image="").count()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Linked {linked_count} photos. Products still without a photo: {remaining_photoless}."
        ))

    def _add_assignment(self, product, photo_path, note, assignments, skipped_duplicate, claimed_product_ids):
        if product.id in claimed_product_ids:
            skipped_duplicate.append((photo_path, product))
            return
        assignments.append((photo_path, product, note))
        claimed_product_ids.add(product.id)

    def _discover_animal_folders(self, base_dir):
        result = {}
        for entry in os.listdir(base_dir):
            full_path = os.path.join(base_dir, entry)
            if not os.path.isdir(full_path):
                continue
            lowered = entry.lower()
            if "dog" in lowered:
                result["Dog"] = full_path
            elif "cat" in lowered:
                result["Cat"] = full_path
        return result
