"""
Import the WILD SIDE grain-free range from "WILD SIDE.docx" and attach photos.

Usage:
    python manage.py import_wildside \\
        --file "/path/to/WILD SIDE.docx" \\
        --photos-dir "/path/to/WILD SIDE_PHOTO&KEIMENA"

The supplier document carries no SKUs and no prices — only recipe copy and pack
sizes — so variants are created at 0.00 € and the products are left inactive on
first import. Set the prices in the admin, tick "is active", and the range goes
live; re-running this command will not switch them back off.
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

# Recipe heading in the document -> product name used on the site.
RECIPES = {
    "AFRICAN SUNSET": "African Sunset ξηρά τροφή - για ενήλικους σκύλους",
    "DEEP FOREST": "Deep Forest ξηρά τροφή - για ενήλικους σκύλους",
    "CANADIAN WHITEWATERS": "Canadian Whitewaters ξηρά τροφή - για ενήλικους σκύλους",
    "NOMAD WINGS": "Nomad Wings ξηρά τροφή - για ενήλικους σκύλους",
    "SALMON HUNTER": "Salmon Hunter ξηρά τροφή - για γάτες",
}

SIZES_RE = re.compile(r"^Διαθέσιμο\s+σε\b", re.IGNORECASE)
WEIGHT_RE = re.compile(r"([\d]+(?:[.,]\d+)?)\s*kg", re.IGNORECASE)
COMPONENTS_RE = re.compile(r"^Σύνθεση\s*:", re.IGNORECASE)
CAT_HINT_RE = re.compile(r"γ[άα]τ", re.IGNORECASE)


def to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_document(file_path: str) -> list[dict]:
    doc = Document(file_path)
    blocks: list[dict] = []
    current: dict | None = None

    for paragraph in doc.paragraphs:
        text = " ".join(paragraph.text.split())
        if not text:
            continue

        heading = text.upper().strip()
        if heading in RECIPES:
            current = {
                "heading": heading,
                "name": RECIPES[heading],
                "description_lines": [],
                "components": "",
                "weights": [],
            }
            blocks.append(current)
            continue

        if current is None:
            continue

        if SIZES_RE.match(text):
            weights = [to_decimal(value) for value in WEIGHT_RE.findall(text)]
            current["weights"] = [w for w in weights if w is not None]
            continue

        if COMPONENTS_RE.match(text):
            current["components"] = text
            continue

        if len(text) > 25:
            current["description_lines"].append(text)

    return [block for block in blocks if block["weights"]]


def find_photo(photos_dir: str, heading: str) -> str | None:
    if not photos_dir or not os.path.isdir(photos_dir):
        return None
    for ext in (".png", ".PNG", ".jpg", ".jpeg", ".webp"):
        path = os.path.join(photos_dir, f"{heading}{ext}")
        if os.path.isfile(path):
            return path
    for fname in os.listdir(photos_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() in {".png", ".jpg", ".jpeg", ".webp"} and stem.upper() == heading:
            return os.path.join(photos_dir, fname)
    return None


class Command(BaseCommand):
    help = "Import the WILD SIDE range (inactive until prices are set) and attach photos."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help='Path to "WILD SIDE.docx"')
        parser.add_argument("--photos-dir", default="", help="Folder with recipe-named photos")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        if not os.path.isfile(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            company = Company.objects.get(name="Wild Side")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'Wild Side' not found. Run seed_data first.") from exc

        animals = {a.name: a for a in AnimalType.objects.all()}
        category = Category.objects.get(name="Dry Food")

        try:
            blocks = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to parse document: {exc}") from exc

        if not blocks:
            raise CommandError("No recipes with pack sizes found in document.")

        created_products = updated_products = 0
        created_variants = updated_variants = 0
        linked_photos = 0
        warnings: list[str] = []

        for block in blocks:
            blob = " ".join(block["description_lines"])
            animal = animals["Cat"] if CAT_HINT_RE.search(blob) else animals["Dog"]
            description = "\n".join(block["description_lines"]).strip()
            photo_path = find_photo(photos_dir, block["heading"])

            if dry_run:
                sizes = ", ".join(f"{w} kg" for w in block["weights"])
                self.stdout.write(
                    f"[DRY RUN] {block['name']} | {animal.name} | {sizes} | "
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
                        "components": block["components"],
                        # Not sellable until someone fills in the prices.
                        "is_active": False,
                    },
                )
                if was_created:
                    created_products += 1
                else:
                    updated_products += 1
                    product.animal_type = animal
                    product.category = category
                    product.description = description
                    product.components = block["components"]
                    product.save(
                        update_fields=[
                            "animal_type",
                            "category",
                            "description",
                            "components",
                            "updated_at",
                        ]
                    )

                if photo_path and (was_created or not product.image):
                    with open(photo_path, "rb") as handle:
                        product.image.save(os.path.basename(photo_path), File(handle), save=True)
                    linked_photos += 1
                elif not photo_path:
                    warnings.append(f"No photo for {block['name']}")

                for weight in block["weights"]:
                    _obj, v_created = ProductVariant.objects.get_or_create(
                        product=product,
                        weight=weight,
                        defaults={
                            "price": Decimal("0.00"),
                            "stock": 0,
                            "availability": ProductVariant.AVAILABILITY_ON_ORDER,
                        },
                    )
                    if v_created:
                        created_variants += 1
                    else:
                        updated_variants += 1

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete: {len(blocks)} recipes."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Products created={created_products} updated={updated_products} | "
                f"Variants created={created_variants} existing={updated_variants} | "
                f"Photos linked={linked_photos}"
            )
        )
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
        if created_products:
            self.stdout.write(
                self.style.WARNING(
                    "New WILD SIDE products are INACTIVE with 0.00 € variants. "
                    "Set prices and tick 'is active' in the admin to publish them."
                )
            )
