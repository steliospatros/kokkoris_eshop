"""
Import Core dog/cat products from Core_Greece_Apr26.docx and attach SKU photos.

Usage:
    python manage.py import_core \\
        --file "/path/to/Core_Greece_Apr26.docx" \\
        --photos-dir "/path/to/PROIONTA"
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

DRY_HEADER_RE = re.compile(
    r"^(PUPPY|JUNIOR|ADULT|SENIOR|ACTIVE|KITTEN|STERILISED)\b",
    re.IGNORECASE,
)
MERGED_DRY_RE = re.compile(
    r"^(?P<header>(?:PUPPY|JUNIOR|ADULT|SENIOR|ACTIVE|KITTEN|STERILISED)"
    r"(?:\s+(?:SMALL|LARGE|LOW FAT|ORIGINAL|OCEAN|LAMB|LIFE))?[^Μ]*?)"
    r"(?P<rest>ΜΕ\s+.+)$",
    re.IGNORECASE,
)
COMPONENTS_START_RE = re.compile(
    r"^(ΣΥΣΤΑΤΙΚΑ|ΑΝΑΛΥΤΙΚΗ|ΜΕΤΑΒΟΛΙΣΤΕΑ)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(
    r"^(?P<value>[\d.,]+)\s*(?P<unit>kg|gr|g)\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"^(?P<price>[\d.,]+)\s*€?")
SKU_RE = re.compile(r"\b(787\d{4}|788\d{4})\b")
FLAVOR_HEADER_RE = re.compile(
    r"^[Α-ΩA-Z0-9 ,&/\-+%]{4,}$",
)
SECTION_SKIP_RE = re.compile(
    r"^(SINGLE PROTEIN|PURELY PATE|TENTER CATS|Η σειρά|Ανακαλύψτε|SUPERPREMIUM)",
    re.IGNORECASE,
)
DOG_HINT_RE = re.compile(r"σκ[ύυ]λ|κουταβ|μικρόσωμ|μεγαλόσωμ", re.IGNORECASE)
CAT_HINT_RE = re.compile(r"γ[άα]τ|γατακ|στείρ", re.IGNORECASE)


def smart_title(text: str) -> str:
    words = []
    for word in text.split():
        if word.isupper() and any(ch.isalpha() for ch in word):
            words.append(word.title())
        else:
            words.append(word)
    return " ".join(words)


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


def is_dry_header(text: str) -> bool:
    if COMPONENTS_START_RE.match(text) or SECTION_SKIP_RE.match(text):
        return False
    if MERGED_DRY_RE.match(text):
        return True
    if DRY_HEADER_RE.match(text) and len(text.split()) <= 6:
        return True
    return False


def is_flavor_header(text: str) -> bool:
    if COMPONENTS_START_RE.match(text) or SECTION_SKIP_RE.match(text):
        return False
    if DRY_HEADER_RE.match(text):
        return False
    if "ΓΙΑ " in text.upper():
        return False
    if " ΜΕ " not in f" {text.upper()} " and "&" not in text:
        return False
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters) >= 0.7


def build_dry_name(header: str) -> str:
    merged = MERGED_DRY_RE.match(header)
    if merged:
        return smart_title(merged.group("header").strip())
    return smart_title(header.strip())


def infer_animal(header: str, subtitle: str, *, in_cat_section: bool, canned_default: str | None) -> str:
    if canned_default:
        return canned_default
    blob = f"{header} {subtitle}"
    if CAT_HINT_RE.search(blob):
        return "Cat"
    if DOG_HINT_RE.search(blob):
        return "Dog"
    if in_cat_section:
        return "Cat"
    return "Dog"


def parse_standard_variants(table) -> list[dict]:
    variants = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if len(cells) < 3:
            continue
        sku = cells[0]
        if not SKU_RE.fullmatch(sku):
            continue
        weight = parse_weight(cells[1])
        price = parse_price(cells[2])
        if weight is None or price is None:
            continue
        variants.append({"sku": sku, "weight": weight, "price": price})
    return variants


def split_weight_and_pack(raw: str) -> tuple[Decimal | None, str]:
    left = raw.split("|")[0].strip()
    return parse_weight(left), raw


def parse_pack_row(cells: list[str]) -> dict | None:
    if len(cells) < 4:
        return None
    sku = cells[0].strip()
    if not SKU_RE.fullmatch(sku):
        return None
    flavor = cells[1].strip()
    weight, _pack = split_weight_and_pack(cells[2])
    price = parse_price(cells[3])
    if weight is None or price is None:
        return None
    return {"sku": sku, "weight": weight, "price": price, "flavor": flavor}


def parse_single_protein_variants(table) -> list[dict]:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if len(cells) < 3:
            continue
        sku = cells[0]
        if not SKU_RE.fullmatch(sku):
            continue
        weight, _pack = split_weight_and_pack(cells[1])
        price = parse_price(cells[2])
        if weight is None or price is None:
            continue
        rows.append({"sku": sku, "weight": weight, "price": price})
    return rows


def classify_table(table) -> str:
    if not table.rows:
        return "standard"
    first = [cell.text.strip().replace("\n", " ") for cell in table.rows[0].cells]
    sample = " | ".join(first).lower()
    if len(first) == 3 and "400 gr" in sample:
        return "single_protein"
    if len(first) >= 4 and "τεµ" in sample or "τεμ" in sample:
        return "pack_row"
    if len(first) >= 3 and parse_weight(first[1]):
        return "standard"
    return "standard"


def parse_pack_rows(table) -> list[dict]:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        parsed = parse_pack_row(cells)
        if parsed:
            rows.append(parsed)
    return rows


def find_photo(photos_dir: str, sku: str) -> str | None:
    if not photos_dir or not sku:
        return None
    for ext in (".png", ".PNG", ".jpg", ".jpeg", ".webp"):
        path = os.path.join(photos_dir, f"{sku}{ext}")
        if os.path.isfile(path):
            return path
    return None


def pick_product_photo(photos_dir: str, variants: list[dict]) -> str | None:
    if not variants:
        return None
    ordered = sorted(variants, key=lambda item: item["weight"])
    for variant in ordered:
        path = find_photo(photos_dir, variant["sku"])
        if path:
            return path
    return None


def parse_document(file_path: str) -> list[dict]:
    doc = Document(file_path)
    blocks: list[dict] = []
    current: dict | None = None
    pending_single_protein: list[dict] = []
    in_cat_section = False
    in_single_protein_section = False

    def flush_current():
        nonlocal current
        if current and current.get("variants"):
            blocks.append(current)
        current = None

    def start_dry_block(header: str, subtitle: str = ""):
        nonlocal current, in_cat_section, in_single_protein_section
        flush_current()
        in_single_protein_section = False
        if header.upper().startswith("KITTEN"):
            in_cat_section = True
        animal = infer_animal(header, subtitle, in_cat_section=in_cat_section, canned_default=None)
        current = {
            "header": header.strip(),
            "subtitle": subtitle.strip(),
            "description_lines": [],
            "components_lines": [],
            "variants": [],
            "animal": animal,
            "category": "Dry Food",
            "name": build_dry_name(header),
        }

    def start_single_protein_block(header: str):
        pending_single_protein.append(
            {
                "header": header.strip(),
                "description_lines": [],
                "components_lines": [],
                "sku": "",
            }
        )

    table_idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = paragraph_text(child)
            if not text:
                continue

            merged = MERGED_DRY_RE.match(text)
            if merged:
                start_dry_block(merged.group("header"), merged.group("rest"))
                continue

            if is_dry_header(text):
                start_dry_block(text)
                continue

            if current is not None and not current["subtitle"] and (
                text.upper().startswith("ΜΕ ") or text.upper().startswith("ΓΙΑ ")
            ):
                current["subtitle"] = text
                current["animal"] = infer_animal(
                    current["header"],
                    text,
                    in_cat_section=in_cat_section,
                    canned_default=None,
                )
                continue

            if current is not None and (
                COMPONENTS_START_RE.match(text) or current["components_lines"]
            ):
                current["components_lines"].append(text)
                continue

            if in_single_protein_section and is_flavor_header(text):
                flush_current()
                start_single_protein_block(text)
                continue

            if in_single_protein_section and pending_single_protein:
                block = pending_single_protein[-1]
                if COMPONENTS_START_RE.match(text):
                    block["components_lines"].append(text)
                elif re.match(r"^\d+%", text):
                    block["description_lines"].append(text)
                else:
                    found = SKU_RE.search(text)
                    if found:
                        block["sku"] = found.group(1)
                    if len(text) > 15:
                        block["description_lines"].append(text)
                continue

            if current is None:
                if text.upper().startswith("SINGLE PROTEIN"):
                    in_single_protein_section = True
                continue

            if len(text) >= 20:
                current.setdefault("description_lines", []).append(text)

        elif tag == "tbl":
            table = doc.tables[table_idx]
            table_idx += 1
            kind = classify_table(table)

            if kind == "pack_row":
                flush_current()
                default_animal = "Cat" if in_cat_section else "Dog"
                prefix = "Savoury Medleys" if not in_cat_section else ""
                for row in parse_pack_rows(table):
                    if prefix and "," in row["flavor"]:
                        name = f"{prefix} - {row['flavor']}"
                    else:
                        name = smart_title(row["flavor"].replace("|", " - "))
                    blocks.append(
                        {
                            "header": row["flavor"],
                            "subtitle": "",
                            "description_lines": [],
                            "components_lines": [],
                            "variants": [
                                {
                                    "sku": row["sku"],
                                    "weight": row["weight"],
                                    "price": row["price"],
                                }
                            ],
                            "animal": default_animal,
                            "category": "Canned Food",
                            "name": name,
                        }
                    )
                if not in_cat_section:
                    in_single_protein_section = True
                continue

            if kind == "single_protein":
                rows = parse_single_protein_variants(table)
                by_sku = {row["sku"]: row for row in rows}
                used = set()
                for item in pending_single_protein:
                    sku = item.get("sku")
                    if not sku or sku not in by_sku:
                        continue
                    used.add(sku)
                    row = by_sku[sku]
                    blocks.append(
                        {
                            "header": item["header"],
                            "subtitle": "",
                            "description_lines": item.get("description_lines") or [],
                            "components_lines": item.get("components_lines") or [],
                            "variants": [
                                {
                                    "sku": row["sku"],
                                    "weight": row["weight"],
                                    "price": row["price"],
                                }
                            ],
                            "animal": "Dog",
                            "category": "Canned Food",
                            "name": smart_title(item["header"]),
                        }
                    )
                for row in rows:
                    if row["sku"] in used:
                        continue
                    blocks.append(
                        {
                            "header": row["sku"],
                            "subtitle": "",
                            "description_lines": [],
                            "components_lines": [],
                            "variants": [row],
                            "animal": "Dog",
                            "category": "Canned Food",
                            "name": f"Single Protein {row['sku']}",
                        }
                    )
                pending_single_protein.clear()
                in_single_protein_section = False
                continue

            if kind == "standard" and current is not None:
                current["variants"].extend(parse_standard_variants(table))
                continue

    flush_current()
    return blocks


class Command(BaseCommand):
    help = "Import Core catalogue products and attach PROIONTA SKU photos."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Core_Greece_Apr26.docx")
        parser.add_argument("--photos-dir", default="", help="Folder with SKU-named PNG files")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        if not os.path.isfile(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            company = Company.objects.get(name="Core")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'Core' not found. Run seed_data first.") from exc

        categories = {c.name: c for c in Category.objects.all()}
        animals = {a.name: a for a in AnimalType.objects.all()}

        try:
            blocks = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to parse document: {exc}") from exc

        blocks = [block for block in blocks if block.get("variants")]
        if not blocks:
            raise CommandError("No products with variants found.")

        created_products = updated_products = 0
        created_variants = updated_variants = 0
        linked_photos = 0
        warnings: list[str] = []

        for block in blocks:
            animal = animals[block["animal"]]
            category = categories[block["category"]]
            name = block["name"]
            if block["category"] == "Dry Food":
                name = f"{name} ({block['animal']})"
            subtitle = block.get("subtitle") or ""
            description_parts = block.get("description_lines") or []
            if subtitle and subtitle not in name:
                description_parts = [subtitle, *description_parts]
            description = "\n".join(description_parts).strip()
            components = "\n".join(block.get("components_lines") or []).strip()
            variants = block.get("variants") or []
            photo_path = pick_product_photo(photos_dir, variants)

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] {name} | {block['animal']} | {block['category']} | "
                    f"{len(variants)} vars | photo={'yes' if photo_path else 'no'}"
                )
                continue

            with transaction.atomic():
                product, was_created = Product.objects.get_or_create(
                    name=name,
                    company=company,
                    defaults={
                        "animal_type": animal,
                        "category": category,
                        "description": description,
                        "components": components,
                    },
                )
                if was_created:
                    created_products += 1
                else:
                    updated_products += 1
                    product.animal_type = animal
                    product.category = category
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

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Dry run complete: {len(blocks)} products."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Products created={created_products} updated={updated_products} | "
                f"Variants created={created_variants} updated={updated_variants} | "
                f"Photos linked={linked_photos}"
            )
        )
        for warning in warnings[:20]:
            self.stdout.write(self.style.WARNING(f"  ! {warning}"))
