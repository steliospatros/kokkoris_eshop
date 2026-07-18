"""
Import PROFINE products from Profine_Greece_Mar26.docx + PROFINE_PHOTO.

Covers:
  - Dry food (dog + cat)
  - Canned Single Protein / 65% (dog)
  - Cat sachets (fillets in jelly)

Usage:
    python manage.py import_profine \\
        --file "/path/to/Profine_Greece_Mar26.docx" \\
        --photos-dir "/path/to/PROFINE_PHOTO"
"""
from __future__ import annotations

import os
import re
import unicodedata
from decimal import Decimal, InvalidOperation

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from docx import Document
from docx.oxml.ns import qn

from products.models import AnimalType, Category, Company, Product, ProductVariant

COMPONENTS_START_RE = re.compile(
    r"^(Σ[ΎΥ]?ΝΘΕΣΗ|ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ|ΜΕΤΑΒΟΛΙΣΤΕΑ|\*\s*Φυσικά)",
    re.IGNORECASE,
)
WEIGHT_RE = re.compile(
    r"^(?P<value>[\d.,]+)\s*(?P<unit>kg|gr|g)\b",
    re.IGNORECASE,
)
PRICE_RE = re.compile(r"^(?P<price>[\d.,]+)\s*€?")

DRY_HEADER_RE = re.compile(
    r"^(PUPPY|JUNIOR|ADULT|SENIOR|ENERGY|LIGHT|KITTEN|ORIGINAL|STERILISED|DERMA)\b",
    re.IGNORECASE,
)
SINGLE_PROTEIN_RE = re.compile(r"^SINGLE PROTEIN\b", re.IGNORECASE)
SIXTY_FIVE_RE = re.compile(r"^65%\s+")
SACHET_RE = re.compile(r"ΙΔΑΝΙΚΗ ΓΙΑ", re.IGNORECASE)

SECTION_SKIP_RE = re.compile(
    r"^(ΚΟΝΣΕΡΒΕΣ|SUPERPREMIUM|ΤΑ ΣΥΣΤΑΤΙΚΑ|Η εξαιρετικής|Οι τροφές|Η διατροφή|"
    r"60-70%|εξασφαλίζει|Ειδικές|ΦΥΚΙΑ|ΣΥΜΠΛΕΓΜΑ|ΑΚΟΜΗ|ΦΑΚΕΛ|"
    r"65%\s*-\s*ΔΥΟ|ΧΩΡΙΣ ΣΙΤΑΡΙ)",
    re.IGNORECASE,
)

DOG_HINT_RE = re.compile(r"σκ[ύυ]λ|κουταβ|μικρ[όο]σωμ|μεγαλ[όο]σωμ", re.IGNORECASE)
CAT_HINT_RE = re.compile(r"γ[άα]τ|γατακ", re.IGNORECASE)

MERGED_DRY_RE = re.compile(
    r"^(?P<header>(?:PUPPY|JUNIOR|ADULT|SENIOR|ENERGY|LIGHT|KITTEN|ORIGINAL|STERILISED|DERMA)"
    r"[A-Z0-9 ,&/\-]*)(?P<rest>ΜΕ\s+.+)$",
    re.IGNORECASE,
)


def fold_greek(text: str) -> str:
    """Normalize lookalike µ/μ and case for matching."""
    text = text.replace("µ", "μ").replace("Μ", "Μ")
    text = unicodedata.normalize("NFKC", text)
    return text.casefold()


def smart_title(text: str) -> str:
    words = []
    for word in text.split():
        if word.isupper() and any(c.isalpha() for c in word):
            words.append(word.title())
        elif word.isupper():
            words.append(word)
        else:
            words.append(word)
    return " ".join(words)


def build_product_name(header: str, category_name: str) -> str:
    cleaned = re.sub(r"\s+ΙΔΑΝΙΚΗ ΓΙΑ.*$", "", header, flags=re.IGNORECASE).strip()
    if category_name == "Sachets":
        return smart_title(cleaned)
    if cleaned.upper().startswith("SINGLE PROTEIN"):
        rest = cleaned[len("SINGLE PROTEIN") :].strip()
        return f"Single Protein {smart_title(rest)}"
    if cleaned.startswith("65%"):
        rest = cleaned[3:].strip()
        return f"65% {smart_title(rest)}"
    return smart_title(cleaned)


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


def classify_category(header: str) -> str:
    if SACHET_RE.search(header) or (
        not DRY_HEADER_RE.match(header)
        and not SINGLE_PROTEIN_RE.match(header)
        and not SIXTY_FIVE_RE.match(header)
        and "ΜΕ " in header.upper()
        and any(ch.isalpha() and ord(ch) > 127 for ch in header)
    ):
        # Greek sachet titles like "ΣΟΛΟΜΟΣ ΜΕ CATNIP ΙΔΑΝΙΚΗ..."
        if SACHET_RE.search(header):
            return "Sachets"
    if SINGLE_PROTEIN_RE.match(header) or SIXTY_FIVE_RE.match(header):
        return "Canned Food"
    if SACHET_RE.search(header):
        return "Sachets"
    return "Dry Food"


def is_product_header(text: str) -> bool:
    if SECTION_SKIP_RE.match(text):
        return False
    if len(text) < 4:
        return False
    if COMPONENTS_START_RE.match(text):
        return False
    if text.upper().startswith("ΜΕ "):
        return False
    if DRY_HEADER_RE.match(text):
        return True
    if SINGLE_PROTEIN_RE.match(text):
        return True
    if SIXTY_FIVE_RE.match(text) and "-" not in text[:6]:
        return True
    if SACHET_RE.search(text):
        return True
    return False


def infer_animal(subtitle: str, header: str, last_animal: str, category: str) -> str:
    # Wet dog cans are always dog in this catalogue.
    if category == "Canned Food" or SINGLE_PROTEIN_RE.match(header) or SIXTY_FIVE_RE.match(header):
        return "Dog"
    if category == "Sachets" or SACHET_RE.search(header):
        return "Cat"
    if CAT_HINT_RE.search(subtitle) or CAT_HINT_RE.search(header):
        return "Cat"
    if DOG_HINT_RE.search(subtitle) or DOG_HINT_RE.search(header):
        return "Dog"
    upper = header.upper()
    if any(tok in upper for tok in ("KITTEN", "STERILISED", "DERMA", "ORIGINAL ADULT", "LIGHT TURKEY")):
        return "Cat"
    if any(tok in upper for tok in ("PUPPY", "JUNIOR", "ADULT", "SENIOR", "ENERGY", "LIGHT LAMB")):
        return "Dog"
    return last_animal


def parse_table_variants(table) -> list[dict]:
    variants = []
    for row in table.rows:
        cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
        if not cells or not cells[0]:
            continue
        sku = cells[0]
        if sku.lower() in {"sku", "κωδικός"}:
            continue
        # Sachets: SKU | 85 gr | 24 τεμ. | 1.10 €
        if len(cells) >= 4:
            weight = parse_weight(cells[1])
            price = parse_price(cells[3])
        elif len(cells) >= 3:
            weight = parse_weight(cells[1])
            price = parse_price(cells[2])
        else:
            continue
        if weight is None or price is None:
            continue
        variants.append({"sku": sku, "weight": weight, "price": price})
    return variants


def parse_document(file_path: str) -> list[dict]:
    doc = Document(file_path)
    blocks: list[dict] = []
    current = None
    last_animal = "Dog"
    in_cat_section = False

    def flush():
        nonlocal current
        if current and current.get("header"):
            blocks.append(current)
        current = None

    def start_block(header: str, subtitle: str = ""):
        nonlocal current, last_animal
        flush()
        category = classify_category(header)
        animal = infer_animal(subtitle, header, "Cat" if in_cat_section else last_animal, category)
        last_animal = animal
        current = {
            "header": header.strip(),
            "subtitle": subtitle,
            "components_lines": [],
            "variants": [],
            "animal": animal,
            "category": category,
        }

    table_idx = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = paragraph_text(child)
            if not text:
                continue

            if "SUPERPREMIUM ΤΡΟΦΗ ΓΙΑ ΓΑΤΕΣ" in text.upper() or "ΤΡΟΦΗ ΓΙΑ ΓΑΤΕΣ" in text.upper():
                in_cat_section = True
                last_animal = "Cat"
                continue
            if text.upper().startswith("ΦΑΚΕΛ"):
                in_cat_section = True
                last_animal = "Cat"
                continue

            merged = MERGED_DRY_RE.match(text)
            if merged:
                header = merged.group("header").strip()
                rest = merged.group("rest").strip()
                start_block(header, rest)
                continue

            if is_product_header(text):
                start_block(text)
                continue

            if current is None:
                continue

            if not current["subtitle"] and (
                text.upper().startswith("ΜΕ ") or "ΓΙΑ " in text.upper()
            ):
                current["subtitle"] = text
                current["animal"] = infer_animal(
                    text, current["header"], current["animal"], current["category"]
                )
                last_animal = current["animal"]
                continue

            if COMPONENTS_START_RE.match(text) or current["components_lines"]:
                current["components_lines"].append(text)
                continue

            # Ignore tiny fragments from broken PDF/Word conversions.
            if len(text) < 20 and not COMPONENTS_START_RE.match(text):
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


def photo_key(stem: str) -> str:
    stem = re.sub(r"_(DOG|CAT)$", "", stem, flags=re.IGNORECASE)
    return fold_greek(stem)


def find_photo(photos_dir: str, header: str, animal_name: str) -> str | None:
    if not photos_dir or not os.path.isdir(photos_dir):
        return None

    animal_suffix = "DOG" if animal_name == "Dog" else "CAT"
    base = re.sub(r"\s+ΙΔΑΝΙΚΗ ΓΙΑ.*$", "", header, flags=re.IGNORECASE).strip()
    # ENERGY merged leftovers already split; normalize spaces around &
    base = re.sub(r"\s+", " ", base)

    candidates = [
        f"{base}_{animal_suffix}.png",
        f"{base}_{animal_suffix}.PNG",
        f"{base}_{animal_suffix}.jpg",
    ]
    for name in candidates:
        path = os.path.join(photos_dir, name)
        if os.path.isfile(path):
            return path

    wanted = photo_key(base)
    best = None
    for fname in os.listdir(photos_dir):
        stem, ext = os.path.splitext(fname)
        if ext.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        if not stem.upper().endswith(f"_{animal_suffix}"):
            continue
        key = photo_key(stem)
        if key == wanted or wanted.startswith(key) or key.startswith(wanted):
            return os.path.join(photos_dir, fname)
        # Soft match: ignore punctuation differences
        soft_wanted = re.sub(r"[^0-9a-zα-ω%]+", "", wanted)
        soft_key = re.sub(r"[^0-9a-zα-ω%]+", "", key)
        if soft_wanted == soft_key:
            best = os.path.join(photos_dir, fname)
    return best


class Command(BaseCommand):
    help = "Import PROFINE catalogue products and attach PROFINE_PHOTO packs."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Profine_Greece_Mar26.docx")
        parser.add_argument("--photos-dir", default="", help="PROFINE_PHOTO folder")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        photos_dir = options["photos_dir"]
        dry_run = options["dry_run"]

        if not os.path.isfile(file_path):
            raise CommandError(f"File not found: {file_path}")

        try:
            company = Company.objects.get(name="PROFINE")
        except Company.DoesNotExist as exc:
            raise CommandError("Company 'PROFINE' not found. Run seed_data first.") from exc

        categories = {c.name: c for c in Category.objects.all()}
        animals = {a.name: a for a in AnimalType.objects.all()}

        try:
            blocks = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to parse document: {exc}") from exc

        if not blocks:
            raise CommandError("No products found.")

        created_products = updated_products = 0
        created_variants = updated_variants = 0
        linked_photos = 0
        warnings = []

        for block in blocks:
            animal = animals[block["animal"]]
            category = categories[block["category"]]
            name = build_product_name(block["header"], block["category"])
            description = block.get("subtitle") or ""
            components = "\n".join(block.get("components_lines") or []).strip()
            variants = block.get("variants") or []
            photo_path = find_photo(photos_dir, block["header"], block["animal"])

            if dry_run:
                self.stdout.write(
                    f"[DRY RUN] {name} | {block['animal']} | {block['category']} | "
                    f"{len(variants)} vars | photo={'yes' if photo_path else 'no'}"
                )
                for variant in variants:
                    self.stdout.write(
                        f"    {variant['sku']} · {variant['weight']} kg · {variant['price']} €"
                    )
                if not variants:
                    warnings.append(f"No price table for {name}")
                if not photo_path:
                    warnings.append(f"No photo for {name} ({block['header']})")
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
