"""
Import the EVER CLEAN cat litter range from "EVER CLEAN.docx" and attach photos.

Usage:
    python manage.py import_everclean \\
        --file "/path/to/EVER CLEAN.docx" \\
        --photos-dir "/path/to/EVER CLEAN_PHOTO&KEIMENA"

The supplier document is prose rather than tables, so the product headings are
listed here explicitly; SKUs, pack sizes, prices and marketing copy are all read
from the document itself.
"""
from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from docx import Document

from products.models import AnimalType, Category, Company, Product, ProductVariant

# Heading exactly as it appears in the document -> product name used on the site.
HEADINGS = {
    "Total Cover": "Άμμος υγιεινής Total Cover",
    "Extra Strong Clumping SCENTED": "Άμμος υγιεινής Extra Strong Clumping με άρωμα",
    "Extra Strong Clumping UNSCENTED": "Άμμος υγιεινής Extra Strong Clumping χωρίς άρωμα",
    "Multiple Cat": "Άμμος υγιεινής Multiple Cat",
    "Litterfree Paws Multi-Crystals": "Άμμος υγιεινής Litterfree Paws Multi-Crystals",
    "Multi-Crystals": "Άμμος υγιεινής Multi-Crystals",
    "Fast Acting Odour Control": "Άμμος υγιεινής Fast Acting Odour Control",
    "Spring Garden": "Άμμος υγιεινής Spring Garden",
    "Lavender": "Άμμος υγιεινής Lavender",
    "Καλωσορίζουμε τη νέα Ever Clean Senior Cat": "Άμμος υγιεινής Senior Cat",
}

# "89204 - 6lt" and "89304 6 lt 16.90 €"
SKU_LINE_RE = re.compile(
    r"^(?P<sku>\d{5})\s*[-–—]?\s*(?P<litres>[\d.,]+)\s*lt\b\s*(?P<price>[\d.,]+)?\s*€?\s*$",
    re.IGNORECASE,
)
# Standalone price list: "6 lt 16.90 €"
PRICE_LINE_RE = re.compile(
    r"^(?P<litres>[\d.,]+)\s*lt\s+(?P<price>[\d.,]+)\s*€\s*$",
    re.IGNORECASE,
)


def to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_document(file_path: str) -> tuple[list[dict], dict[Decimal, Decimal], str]:
    """Return (product blocks, price-per-pack-size, brand intro paragraph)."""
    doc = Document(file_path)
    blocks: list[dict] = []
    prices: dict[Decimal, Decimal] = {}
    intro = ""
    current: dict | None = None

    for paragraph in doc.paragraphs:
        text = " ".join(paragraph.text.split())
        if not text:
            continue

        if not intro and text.lower().startswith("extra δυνατή"):
            intro = text

        if text in HEADINGS:
            current = {
                "name": HEADINGS[text],
                "heading": text,
                "description_lines": [],
                "variants": [],
            }
            blocks.append(current)
            continue

        sku_match = SKU_LINE_RE.match(text)
        if sku_match:
            litres = to_decimal(sku_match.group("litres"))
            price = to_decimal(sku_match.group("price") or "")
            if current is not None and litres is not None:
                current["variants"].append(
                    {
                        "sku": sku_match.group("sku"),
                        "litres": litres,
                        "price": price,
                    }
                )
                if price is not None:
                    prices.setdefault(litres, price)
            continue

        price_match = PRICE_LINE_RE.match(text)
        if price_match:
            litres = to_decimal(price_match.group("litres"))
            price = to_decimal(price_match.group("price"))
            if litres is not None and price is not None:
                prices[litres] = price
            continue

        if current is not None and not current["variants"] and len(text) > 25:
            current["description_lines"].append(text)

    return [block for block in blocks if block["variants"]], prices, intro


def find_photo(photos_dir: str, sku: str) -> str | None:
    if not photos_dir or not sku:
        return None
    for ext in (".png", ".PNG", ".jpg", ".jpeg", ".webp"):
        path = os.path.join(photos_dir, f"{sku}{ext}")
        if os.path.isfile(path):
            return path
    return None


def pick_product_photo(photos_dir: str, variants: list[dict]) -> str | None:
    for variant in sorted(variants, key=lambda item: item["litres"]):
        path = find_photo(photos_dir, variant["sku"])
        if path:
            return path
    return None


class Command(BaseCommand):
    help = "Import the EVER CLEAN cat litter range and attach SKU photos."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help='Path to "EVER CLEAN.docx"')
        parser.add_argument("--photos-dir", default="", help="Folder with SKU-named photos")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        if not os.path.isfile(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            company = Company.objects.get(name="EVERCLEAN")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'EVERCLEAN' not found. Run seed_data first.") from exc

        animal = AnimalType.objects.get(name="Cat")
        category = Category.objects.get(name="Litter")

        try:
            blocks, prices, intro = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to parse document: {exc}") from exc

        if not blocks:
            raise CommandError("No products with SKUs found in document.")

        missing = sorted(
            {
                str(variant["litres"])
                for block in blocks
                for variant in block["variants"]
                if variant["price"] is None and variant["litres"] not in prices
            }
        )
        if missing:
            raise CommandError(f"No price found for pack sizes: {', '.join(missing)} lt")

        created_products = updated_products = 0
        created_variants = updated_variants = 0
        linked_photos = 0
        warnings: list[str] = []

        for block in blocks:
            description = "\n".join(block["description_lines"]).strip()
            photo_path = pick_product_photo(photos_dir, block["variants"])

            if dry_run:
                sizes = ", ".join(
                    f"{variant['sku']}·{variant['litres']}L"
                    for variant in block["variants"]
                )
                self.stdout.write(
                    f"[DRY RUN] {block['name']} | {sizes} | "
                    f"photo={'yes' if photo_path else 'no'}"
                )
                continue

            with transaction.atomic():
                product, was_created = Product.objects.get_or_create(
                    name=block["name"],
                    company=company,
                    defaults={
                        "animal_type": animal,
                        "category": category,
                        "description": description,
                    },
                )
                if was_created:
                    created_products += 1
                else:
                    updated_products += 1
                    product.animal_type = animal
                    product.category = category
                    product.description = description
                    product.save(
                        update_fields=["animal_type", "category", "description", "updated_at"]
                    )

                if photo_path and (was_created or not product.image):
                    with open(photo_path, "rb") as handle:
                        product.image.save(os.path.basename(photo_path), File(handle), save=True)
                    linked_photos += 1
                elif not photo_path:
                    warnings.append(f"No photo for {block['name']}")

                for variant in block["variants"]:
                    price = variant["price"] or prices[variant["litres"]]
                    _obj, v_created = ProductVariant.objects.update_or_create(
                        sku=variant["sku"],
                        defaults={
                            "product": product,
                            "weight": variant["litres"],
                            "price": price,
                        },
                    )
                    if v_created:
                        created_variants += 1
                    else:
                        updated_variants += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete: {len(blocks)} products, "
                    f"prices {dict(sorted(prices.items()))}"
                )
            )
            return

        if intro and not company.description:
            company.description = intro
            company.save(update_fields=["description"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Products created={created_products} updated={updated_products} | "
                f"Variants created={created_variants} updated={updated_variants} | "
                f"Photos linked={linked_photos}"
            )
        )
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
