"""
Import OWNAT Classic dry-food products from the Greek catalogue Word file
and attach pack photos from the matching photo folder.

Source layout (body order):
    HEADER (ALL CAPS Latin, e.g. "JUNIOR - CHICKEN" or "COMPLET")
    Greek subtitle (description)
    ΣΥΝΘΕΣΗ / ΑΝΑΛΥΤΙΚΑ / ΕΝΕΡΓΕΙΑ paragraphs (components)
    Word table: SKU | weight | price rows

Photos in the same folder are named like:
    JUNIOR - CHICKEN_DOG.png
    ADULT - FISH_CAT.png
    COMPLET_DOG.png

Usage:
    python manage.py import_ownat_classic \\
        --file "/path/to/OwnatClassic_Greece_Aug24.docx" \\
        --photos-dir "/path/to/OWNAT CLASSIC PHOTO"

    python manage.py import_ownat_classic --file ... --photos-dir ... --dry-run
"""
from __future__ import annotations

import os
import re
from decimal import Decimal, InvalidOperation

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from docx import Document
from docx.oxml.ns import qn

from products.models import AnimalType, Category, Company, Product, ProductVariant

HEADER_RE = re.compile(
    r"^[A-Z0-9][A-Z0-9 &/\-]*$"
)
COMPONENTS_START_RE = re.compile(
    r"^(ΣΥΝΘΕΣΗ|ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ|ΜΕΤΑΒΟΛΙΣΤΕΑ|Μεταβολιστέα|\*Φυσικά)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(
    r"^(?P<value>[\d.,]+)\s*(?P<unit>kg|gr|g)\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(
    r"^(?P<price>[\d.,]+)\s*€?",
)
DOG_HINT_RE = re.compile(
    r"σκ[ύυ]λ|κουταβ|μικρ[όο]σωμ",
    re.IGNORECASE,
)
CAT_HINT_RE = re.compile(
    r"γ[άα]τ|γατακ",
    re.IGNORECASE,
)

# Headers that exist for both dog and cat — need unique Product.name / slug.
DISAMBIGUATE_HEADERS = {
    "ADULT - FISH",
    "LIGHT - CHICKEN",
}


def smart_title(text: str) -> str:
    words = []
    for word in text.split():
        if word.isupper() and any(c.isalpha() for c in word):
            words.append(word.title())
        else:
            words.append(word)
    return " ".join(words)


def format_header_title(header: str) -> str:
    return " - ".join(smart_title(part) for part in header.split(" - "))


def parse_weight(raw: str) -> Decimal | None:
    m = WEIGHT_RE.match(raw.strip())
    if not m:
        return None
    value = Decimal(m.group("value").replace(",", "."))
    unit = m.group("unit").lower()
    if unit in {"gr", "g"}:
        return (value / Decimal("1000")).quantize(Decimal("0.001"))
    return value


def parse_price(raw: str) -> Decimal | None:
    m = PRICE_RE.match(raw.strip().replace(" ", ""))
    if not m:
        return None
    try:
        return Decimal(m.group("price").replace(",", "."))
    except InvalidOperation:
        return None


def paragraph_text(element) -> str:
    texts = [node.text for node in element.iter(qn("w:t")) if node.text]
    return "".join(texts).strip()


def infer_animal(subtitle: str, header: str, last_animal: str | None) -> str | None:
    if CAT_HINT_RE.search(subtitle):
        return "Cat"
    if DOG_HINT_RE.search(subtitle):
        return "Dog"
    upper = header.upper()
    if any(token in upper for token in ("KITTEN", "HAIRBALL", "STERILIZED", "DAILY CARE")):
        return "Cat"
    if any(
        token in upper
        for token in ("JUNIOR", "COMPLET", "MINI ADULT", "ENERGY", "DUCK", "LAMB")
    ):
        return "Dog"
    # Ambiguous subtitles (e.g. weight-control) inherit the current catalogue section.
    return last_animal


def build_product_name(header: str, animal_name: str) -> str:
    title = format_header_title(header)
    name = f"Classic {title}"
    if header.upper() in DISAMBIGUATE_HEADERS:
        name = f"{name} ({animal_name})"
    return name


def parse_table_variants(table) -> list[dict]:
    variants = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if len(cells) < 3:
            continue
        sku, weight_raw, price_raw = cells[0], cells[1], cells[2]
        if not sku or sku.lower() in {"sku", "κωδικός"}:
            continue
        weight = parse_weight(weight_raw)
        price = parse_price(price_raw)
        if weight is None or price is None:
            continue
        variants.append({"sku": sku, "weight": weight, "price": price})
    return variants


def parse_document(file_path: str) -> list[dict]:
    doc = Document(file_path)
    blocks: list[dict] = []
    current = None
    last_animal: str | None = "Dog"

    def flush():
        nonlocal current
        if current and current.get("header"):
            blocks.append(current)
        current = None

    table_idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = paragraph_text(child)
            if not text or text.upper().startswith("ΠΟΙΟΤΗΤΑ"):
                continue

            if HEADER_RE.match(text) and not text.startswith("ΜΕ "):
                flush()
                current = {
                    "header": text.strip(),
                    "subtitle": "",
                    "components_lines": [],
                    "variants": [],
                    "animal": None,
                }
                continue

            if current is None:
                continue

            if not current["subtitle"] and (
                text.upper().startswith("ΜΕ ") or "ΓΙΑ " in text.upper()
            ):
                current["subtitle"] = text
                animal = infer_animal(text, current["header"], last_animal)
                current["animal"] = animal
                if animal:
                    last_animal = animal
                continue

            if COMPONENTS_START_RE.match(text) or current["components_lines"]:
                if COMPONENTS_START_RE.match(text) or text.startswith("*") or current["components_lines"]:
                    current["components_lines"].append(text)
                    continue

            if current["subtitle"]:
                current["subtitle"] = f"{current['subtitle']} {text}".strip()
            else:
                current["subtitle"] = text

        elif tag == "tbl":
            table = doc.tables[table_idx]
            table_idx += 1
            if current is None:
                continue
            current["variants"].extend(parse_table_variants(table))

    flush()
    return blocks


def find_photo(photos_dir: str, header: str, animal_name: str) -> str | None:
    if not photos_dir or not os.path.isdir(photos_dir):
        return None
    animal_suffix = "DOG" if animal_name == "Dog" else "CAT"
    # Exact: "JUNIOR - CHICKEN_DOG.png" / "COMPLET_DOG.png"
    candidates = [
        f"{header}_{animal_suffix}.png",
        f"{header}_{animal_suffix}.PNG",
        f"{header}_{animal_suffix}.jpg",
    ]
    for name in candidates:
        path = os.path.join(photos_dir, name)
        if os.path.isfile(path):
            return path
    # Case-insensitive scan fallback.
    target = f"{header}_{animal_suffix}".upper()
    for fname in os.listdir(photos_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        if stem.upper() == target:
            return os.path.join(photos_dir, fname)
    return None


class Command(BaseCommand):
    help = "Import OWNAT Classic products from the Greece Aug24 catalogue + photos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to OwnatClassic_Greece_Aug24.docx",
        )
        parser.add_argument(
            "--photos-dir",
            default="",
            help="Folder with OWNAT Classic pack PNGs (optional but recommended).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and print summary without writing to the database.",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        if not os.path.isfile(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            company = Company.objects.get(name="OWNAT")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'OWNAT' not found. Run seed_data first.") from exc

        dry_food = Category.objects.get(name="Dry Food")
        animals = {a.name: a for a in AnimalType.objects.all()}

        try:
            blocks = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to parse document: {exc}") from exc

        if not blocks:
            raise CommandError("No products found in document.")

        created_products = 0
        updated_products = 0
        created_variants = 0
        updated_variants = 0
        linked_photos = 0
        skipped_no_animal = 0
        warnings = []

        for block in blocks:
            animal_name = block.get("animal")
            if animal_name not in animals:
                skipped_no_animal += 1
                warnings.append(f"No animal for header {block['header']!r}")
                continue

            name = build_product_name(block["header"], animal_name)
            animal = animals[animal_name]
            description = block.get("subtitle") or ""
            components = "\n".join(block.get("components_lines") or []).strip()
            variants = block.get("variants") or []
            photo_path = find_photo(photos_dir, block["header"], animal_name)

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] {name} | {animal_name} | "
                    f"{len(variants)} variants | photo={'yes' if photo_path else 'no'}"
                )
                for variant in variants:
                    self.stdout.write(
                        f"    {variant['sku']} · {variant['weight']} kg · {variant['price']} €"
                    )
                if not variants:
                    warnings.append(f"No price table for {name}")
                continue

            with transaction.atomic():
                product, was_created = Product.objects.get_or_create(
                    name=name,
                    company=company,
                    defaults={
                        "animal_type": animal,
                        "category": dry_food,
                        "description": description,
                        "components": components,
                    },
                )
                if was_created:
                    created_products += 1
                else:
                    updated_products += 1
                    product.animal_type = animal
                    product.category = dry_food
                    product.description = description
                    product.components = components
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
                        product.image.save(
                            os.path.basename(photo_path),
                            File(handle),
                            save=True,
                        )
                    linked_photos += 1

                if not variants:
                    warnings.append(f"No price table for {name}")

                for variant in variants:
                    obj, v_created = ProductVariant.objects.update_or_create(
                        sku=variant["sku"],
                        defaults={
                            "product": product,
                            "weight": variant["weight"],
                            "price": variant["price"],
                        },
                    )
                    if v_created:
                        created_variants += 1
                    else:
                        updated_variants += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Products created={created_products} updated={updated_products} | "
                f"Variants created={created_variants} updated={updated_variants} | "
                f"Photos linked={linked_photos} | skipped_no_animal={skipped_no_animal}"
            )
        )
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
