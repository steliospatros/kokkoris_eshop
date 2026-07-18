"""
Import OWNAT Ultra dry-food products from the dog/cat catalogue Word files
and attach pack photos from the OWNAT ULTRA folder.

Usage:
    python manage.py import_ownat_ultra \\
        --dog-file "/path/to/OwnatUltraDOG_New_Apr25_Low.docx" \\
        --cat-file "/path/to/OwnatUltraCAT_New_Apr25_Low.docx" \\
        --photos-dir "/path/to/OWNAT ULTRA"

    python manage.py import_ownat_ultra ... --dry-run
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

HEADER_RE = re.compile(r"^ULTRA[A-Z0-9 \-]*$")
MERGED_HEADER_RE = re.compile(
    r"^(?P<header>ULTRA[A-Z0-9 \-]*?)(?P<rest>ΜΕ\s+.+)$",
)
COMPONENTS_START_RE = re.compile(
    r"^(Σ?ΥΝΘΕΣΗ|ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ|ΜΕΤΑΒΟΛΙΣΤΕΑ|Μεταβολιστέα|\*\s*Φυσικά)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(
    r"^(?P<value>[\d.,]+)\s*(?P<unit>kg|gr|g)\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"^(?P<price>[\d.,]+)\s*€?")


def smart_title(text: str) -> str:
    words = []
    for word in text.split():
        if word.isupper() and any(c.isalpha() for c in word):
            words.append(word.title())
        else:
            words.append(word)
    return " ".join(words)


def format_header_title(header: str) -> str:
    # Drop leading "ULTRA " — product name will use "Ultra ..." prefix once.
    cleaned = re.sub(r"^ULTRA\s+", "", header.strip(), flags=re.IGNORECASE)
    return " - ".join(smart_title(part) for part in cleaned.split(" - "))


def build_product_name(header: str) -> str:
    return f"Ultra {format_header_title(header)}"


def parse_weight(raw: str) -> Decimal | None:
    m = WEIGHT_RE.match(raw.strip())
    if not m:
        return None
    value = Decimal(m.group("value").replace(",", "."))
    unit = m.group("unit").lower()
    if unit in {"gr", "g"}:
        # Real Ultra small packs are 400 gr. Values like "1.5 gr" / "3 gr" are
        # catalogue typos and mean kilograms.
        if value >= 100:
            return (value / Decimal("1000")).quantize(Decimal("0.001"))
        return value
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


def fix_composition_typo(text: str) -> str:
    if text.startswith("ΥΝΘΕΣΗ"):
        return "Σ" + text
    return text


def split_merged_paragraph(text: str) -> tuple[str, str, str] | None:
    """
    Some CAT catalogue paragraphs glue header + subtitle + composition:
    ``ULTRA KITTENΜΕ ΚΟΤΟΠΟΥΛΟ ... ΣΥΝΘΕΣΗ: ...``
    """
    m = MERGED_HEADER_RE.match(text)
    if not m:
        return None
    header = m.group("header").strip()
    rest = m.group("rest").strip()
    subtitle = rest
    components = ""
    for marker in ("ΣΥΝΘΕΣΗ:", "ΥΝΘΕΣΗ:", "ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ:"):
        idx = rest.find(marker)
        if idx > 0:
            subtitle = rest[:idx].strip()
            components = fix_composition_typo(rest[idx:].strip())
            break
    return header, subtitle, components


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


def parse_document(file_path: str, animal_name: str) -> list[dict]:
    doc = Document(file_path)
    blocks: list[dict] = []
    current = None

    def flush():
        nonlocal current
        if current and current.get("header"):
            blocks.append(current)
        current = None

    def start_block(header: str, subtitle: str = "", components: str = ""):
        nonlocal current
        flush()
        current = {
            "header": header,
            "subtitle": subtitle,
            "components_lines": [components] if components else [],
            "variants": [],
            "animal": animal_name,
        }

    table_idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = paragraph_text(child)
            if not text:
                continue

            merged = split_merged_paragraph(text)
            if merged:
                header, subtitle, components = merged
                start_block(header, subtitle, components)
                continue

            if HEADER_RE.match(text):
                start_block(text.strip())
                continue

            if current is None:
                continue

            if not current["subtitle"] and (
                text.upper().startswith("ΜΕ ") or "ΓΙΑ " in text.upper()
            ):
                current["subtitle"] = text
                continue

            fixed = fix_composition_typo(text)
            if COMPONENTS_START_RE.match(fixed) or current["components_lines"]:
                current["components_lines"].append(fixed)
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
    candidates = [
        f"{header}_{animal_suffix}.png",
        f"{header}_{animal_suffix}.PNG",
        f"{header}_{animal_suffix}.jpg",
    ]
    for name in candidates:
        path = os.path.join(photos_dir, name)
        if os.path.isfile(path):
            return path
    target = f"{header}_{animal_suffix}".upper()
    for fname in os.listdir(photos_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        if stem.upper() == target:
            return os.path.join(photos_dir, fname)
    return None


class Command(BaseCommand):
    help = "Import OWNAT Ultra products from dog/cat Apr25 catalogues + photos."

    def add_arguments(self, parser):
        parser.add_argument("--dog-file", default="", help="OwnatUltraDOG_*.docx path")
        parser.add_argument("--cat-file", default="", help="OwnatUltraCAT_*.docx path")
        parser.add_argument(
            "--photos-dir",
            default="",
            help="Folder with ULTRA *_DOG.png / *_CAT.png packs",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dog_file = options["dog_file"]
        cat_file = options["cat_file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        sources = []
        if dog_file:
            sources.append((dog_file, "Dog"))
        if cat_file:
            sources.append((cat_file, "Cat"))
        if not sources:
            raise CommandError("Provide at least --dog-file and/or --cat-file.")

        for path, _animal in sources:
            if not os.path.isfile(path):
                raise CommandError(f"File not found: {path}")

        try:
            company = Company.objects.get(name="OWNAT")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'OWNAT' not found. Run seed_data first.") from exc

        dry_food = Category.objects.get(name="Dry Food")
        animals = {a.name: a for a in AnimalType.objects.all()}

        blocks: list[dict] = []
        for path, animal_name in sources:
            try:
                blocks.extend(parse_document(path, animal_name))
            except Exception as exc:
                raise CommandError(f"Failed to parse {path}: {exc}") from exc

        if not blocks:
            raise CommandError("No products found in documents.")

        created_products = 0
        updated_products = 0
        created_variants = 0
        updated_variants = 0
        linked_photos = 0
        warnings = []

        for block in blocks:
            animal_name = block["animal"]
            animal = animals[animal_name]
            name = build_product_name(block["header"])
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
                if not photo_path:
                    warnings.append(f"No photo for {name} ({block['header']}_{animal_name.upper()})")
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
                if not photo_path:
                    warnings.append(f"No photo for {name}")

                for variant in variants:
                    _obj, v_created = ProductVariant.objects.update_or_create(
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
                f"Photos linked={linked_photos}"
            )
        )
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
