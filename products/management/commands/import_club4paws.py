"""
Imports CLUB4PAWS dog/cat food products from a semi-structured Word (.docx)
catalog file into the database.

The source document is not a clean table - it is a sequence of paragraphs
that follows a repeating (but not perfectly consistent) pattern per product:

    <LIFE-STAGE HEADER, e.g. "ADULT SMALL BREEDS">   (ALL CAPS)
    <FLAVOR HEADER, e.g. "ΜΕ ΚΟΤΟΠΟΥΛΟ">              (ALL CAPS, optional)
    <SKU/WEIGHT/PRICE lines, e.g. "71C3102/2 KG/Λ.Τ.: 11.50€">  (1 or more)
    <ΠΡΩΤΕΪΝΗ/ΛΙΠΑΡΑ quick summary line>              (optional)
    <marketing bullet points and paragraphs>          (free text -> description)
    ΣΥΝΘΕΣΗ: ...                                       (composition -> components)
    ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ: ...                           (-> components)
    ΠΡΟΣΘΕΤΑ: ...                                      (-> components)
    Μεταβολιστέα ενέργεια: ...                         (-> components)

Header lines are identified by being fully upper-case (once known lowercase
Greek filler words like "σε σάλτσα" are stripped for the check). This is a
reliable signal in this specific document, since all marketing/description
text uses normal sentence case.

Usage:
    python manage.py import_club4paws --file "/path/to/OLA TA KEIMENA.docx"

This command is idempotent: re-running it will not create duplicate
Products (matched by name) or ProductVariants (matched by SKU, or by
product+weight when no SKU is available).
"""
import re

import docx
from django.core.management.base import BaseCommand, CommandError

from products.models import AnimalType, Category, Company, Product, ProductVariant

# --- Regex patterns used to classify each paragraph line -------------------

VARIANT_RE = re.compile(
    r'^(?P<sku>[0-9A-Za-zΜM]+)\s*/\s*(?P<weight>[\d.,]+)\s*(?P<unit>KG|GR)\s*/\s*Λ\.Τ\.\s*:\s*(?P<price>[\d.,]+)\s*€',
    re.IGNORECASE,
)
# Multipack / variety-pack lines look different from a regular single-flavor
# variant line: they describe a quantity of small pouches bundled together,
# e.g. "86C210Μ/4 X 85 GR /X.Τ.: 2.22€ Π.Τ.Λ.: 2.75€" which reads as
# SKU / (qty x unit weight) / wholesale price (X.Τ.) / suggested retail price (Π.Τ.Λ.).
# The quantity can also be a promo notation like "5+1" (5 paid + 1 free = 6 units).
# We use the suggested retail price (Π.Τ.Λ.) as the sale price, mirroring how
# Λ.Τ. (retail price) is used for regular single-flavor variants.
MULTIPACK_VARIANT_RE = re.compile(
    r'^(?P<sku>[0-9A-Za-zΜM]+)\s*/\s*(?P<qty>\d+(?:\+\d+)?)\s*[xXΧ]\s*(?P<weight>[\d.,]+)\s*(?P<unit>KG|GR)\s*/\s*[XΧ]\.Τ\.\s*:\s*[\d.,]+\s*€\s*Π\.Τ\.Λ\.\s*:\s*(?P<price>[\d.,]+)\s*€',
    re.IGNORECASE,
)
# Inside a multipack's description, each bundled flavor is listed on its own
# line prefixed with a lowercase quantity marker, e.g. "2χ ΚΟΤΟΠΟΥΛΟ ΣΕ ΣΑΛΤΣΑ"
# ("2x Chicken in Gravy"). The lowercase "χ" is what keeps these lines from
# being mistaken for ALL-CAPS headers.
BUNDLE_FLAVOR_LINE_RE = re.compile(r'^(?P<qty>\d+)\s*[χx]\s*(?P<flavor>.+)$', re.IGNORECASE)

# Restores proper Greek accents on flavor words that were typed without them
# in the source document's ALL-CAPS headers, for a nicer customer-facing
# Greek description (e.g. "ΚΟΤΟΠΟΥΛΟ" -> "κοτόπουλο").
GREEK_ACCENT_FIXES = {
    "κοτοπουλο": "κοτόπουλο",
    "μοσχαρι": "μοσχάρι",
    "σκουμπρι": "σκουμπρί",
    "σολομος": "σολομός",
    "βοδινο": "βοδινό",
    "γαλοπουλα": "γαλοπούλα",
    "κουνελι": "κουνέλι",
    "παπια": "πάπια",
    "σαλτσα": "σάλτσα",
    "ζελε": "ζελέ",
}


def fix_greek_accents(text):
    for wrong, right in GREEK_ACCENT_FIXES.items():
        text = re.sub(rf'\b{wrong}\b', right, text, flags=re.IGNORECASE)
    return text
PROTEIN_FAT_RE = re.compile(r'^ΠΡΩΤΕΪΝΗ')
COMPONENTS_START_RE = re.compile(r'^(ΣΥΝΘΕΣΗ|ΑΝΑΛΥΤΙΚΑ ΣΥΣΤΑΤΙΚΑ|ΠΡΟΣΘΕΤΑ|Μεταβολιστέα|Τεχνολογικά)')
FLAVOR_SUFFIX_RE = re.compile(r'^(σε σάλτσα|σε ζελέ)$', re.IGNORECASE)
FLAVOR_MARKER_RE = re.compile(r'[ΜM][ΕE]\s+')
KNOWN_LOWERCASE_FILLERS_RE = re.compile(
    r'σε σάλτσα|σε ζελέ|για γάτες\s*\+?\s*\d*|για σκύλους', re.IGNORECASE
)
# Some life-stage headers were typed with Greek look-alike letters by mistake
# (e.g. Greek 'Α' instead of Latin 'A'). Safe to normalize since life-stage
# labels are always meant to be Latin/English words in this catalogue.
GREEK_TO_LATIN_HOMOGLYPHS = str.maketrans("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧ", "ABEZHIKMNOPTYX")

FLAVOR_TRANSLATIONS = {
    "ΚΟΤΟΠΟΥΛΟ": "Chicken",
    "ΑΡΝΙ": "Lamb",
    "ΡΥΖΙ": "Rice",
    "ΠΑΠΙΑ": "Duck",
    "ΓΑΛΟΠΟΥΛΑ": "Turkey",
    "ΣΟΛΟΜΟΣ": "Salmon",
    "ΣΟΛΟΜΟ": "Salmon",
    "ΜΟΣΧΑΡΙ": "Beef",
    "ΒΟΔΙΝΟ": "Beef",
    "ΚΟΥΝΕΛΙ": "Rabbit",
    "KOYNEΛΙ": "Rabbit",
    "ΣΚΟΥΜΠΡΙ": "Mackerel",
    "σε σάλτσα": "in Gravy",
    "σε ζελέ": "in Jelly",
    # ALL-CAPS headers in the source document are typed without accents
    # (e.g. "ΣΕ ΣΑΛΤΣΑ" instead of "σε σάλτσα"), so we also match the
    # unaccented forms explicitly - Python's IGNORECASE does not treat
    # accented and unaccented Greek vowels as equivalent.
    "σε σαλτσα": "in Gravy",
    "σε ζελε": "in Jelly",
}

# Known duplicate/erroneous SKUs found in the source catalogue: the same SKU
# code was mistakenly reused for two different flavors ("Indoor 4in1 Chicken"
# and "Indoor 4in1 Lamb"). We keep the SKU on the first occurrence only, and
# leave it blank for the rest to avoid a database uniqueness conflict.
KNOWN_DUPLICATE_SKUS = {"81C6202", "81C6204"}


def is_all_caps_header(line):
    stripped = KNOWN_LOWERCASE_FILLERS_RE.sub('', line)
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    return all(c.isupper() for c in letters)


def translate_words(text, mapping):
    for gr, en in mapping.items():
        text = re.sub(re.escape(gr), en, text, flags=re.IGNORECASE)
    return text


def smart_title(text):
    words = []
    for w in text.split():
        words.append(w.title() if w.isupper() and any(c.isalpha() for c in w) else w)
    return " ".join(words)


def split_header_line(line):
    m = FLAVOR_MARKER_RE.search(line)
    if m:
        return line[:m.start()].strip(), line[m.start():].strip()
    return line.strip(), ""


def clean_life_stage(text):
    text = re.sub(r'γ[ιί]α\s+γ[άα]τ[εέ]ς\s*\+?\s*7\+?', 'For Cats 7+', text, flags=re.IGNORECASE)
    text = text.translate(GREEK_TO_LATIN_HOMOGLYPHS)
    text = smart_title(text)
    return " ".join(text.split()).strip(" -")


def clean_flavor(text):
    text = FLAVOR_MARKER_RE.sub("", text, count=1)
    text = translate_words(text, FLAVOR_TRANSLATIONS)
    text = text.replace("&", "and")
    return " ".join(text.split())


def new_block(animal):
    return {
        "animal": animal,
        "life_stage_parts": [],
        "flavor_parts": [],
        "protein_fat": "",
        "description_lines": [],
        "components_lines": [],
        "variants": [],
        "is_bundle": False,
    }


def build_bundle_flavor_summary(description_lines):
    """
    Turns raw bundle description lines like "2χ ΚΟΤΟΠΟΥΛΟ ΣΕ ΣΑΛΤΣΑ" into a
    clean, translated, Latin-character summary such as "2x Chicken in Gravy",
    used for the Product.bundle_contents field.
    """
    parts = []
    for line in description_lines:
        m = BUNDLE_FLAVOR_LINE_RE.match(line)
        if not m:
            continue
        flavor = translate_words(m.group("flavor"), FLAVOR_TRANSLATIONS)
        flavor = " ".join(flavor.split())
        parts.append(f"{m.group('qty')}x {smart_title(flavor)}")
    return ", ".join(parts)


def build_bundle_description(description_lines):
    """
    Builds a short, readable Greek description for a bundle from its raw
    flavor lines, e.g. "Περιέχει: 2χ Κοτόπουλο σε σάλτσα, 2χ Σολομός σε ζελέ."
    """
    cleaned = []
    for line in description_lines:
        m = BUNDLE_FLAVOR_LINE_RE.match(line)
        if not m:
            continue
        flavor_text = fix_greek_accents(m.group("flavor").strip().lower()).capitalize()
        cleaned.append(f"{m.group('qty')}χ {flavor_text}")
    if not cleaned:
        return ""
    return "Περιέχει: " + ", ".join(cleaned) + "."


def parse_document(path):
    """Parses the .docx file into a list of raw product blocks (dicts)."""
    doc = docx.Document(path)
    lines = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    products = []
    current_animal = None
    block = None
    collecting_header = True

    def flush_block():
        if block is not None and (block["life_stage_parts"] or block["flavor_parts"]):
            products.append(block)

    for line in lines:
        if line in ("DOGS", "CATS"):
            current_animal = "Dog" if line == "DOGS" else "Cat"
            continue

        # Multipack lines are checked before the regular VARIANT_RE, because
        # their SKU/qty/price line comes *after* the flavor list in the
        # source document (unlike single-flavor products, where it comes
        # first) and would otherwise be misread as the header of the next
        # product, silently dropping the whole bundle.
        multipack_match = MULTIPACK_VARIANT_RE.match(line)
        if multipack_match:
            qty_raw = multipack_match.group("qty")
            total_units = sum(int(n) for n in qty_raw.split("+"))
            unit_weight_raw = float(multipack_match.group("weight").replace(",", "."))
            unit = multipack_match.group("unit").upper()
            unit_weight_kg = unit_weight_raw / 1000 if unit == "GR" else unit_weight_raw
            total_weight_kg = round(unit_weight_kg * total_units, 3)
            price = float(multipack_match.group("price").replace(",", "."))
            if block is None:
                block = new_block(current_animal)
            block["is_bundle"] = True
            block["variants"].append({
                "sku": multipack_match.group("sku"),
                "weight_kg": total_weight_kg,
                "price": price,
            })
            collecting_header = False
            continue

        variant_match = VARIANT_RE.match(line)
        if variant_match:
            weight_raw = float(variant_match.group("weight").replace(",", "."))
            unit = variant_match.group("unit").upper()
            weight_kg = weight_raw / 1000 if unit == "GR" else weight_raw
            price = float(variant_match.group("price").replace(",", "."))
            if block is None:
                block = new_block(current_animal)
            block["variants"].append({
                "sku": variant_match.group("sku"),
                "weight_kg": round(weight_kg, 3),
                "price": price,
            })
            collecting_header = False
            continue

        if PROTEIN_FAT_RE.match(line):
            if block is None:
                block = new_block(current_animal)
            block["protein_fat"] = line
            collecting_header = False
            continue

        if COMPONENTS_START_RE.match(line):
            if block is None:
                block = new_block(current_animal)
            block["components_lines"].append(line)
            collecting_header = False
            continue

        is_header = is_all_caps_header(line) or FLAVOR_SUFFIX_RE.match(line)
        if is_header:
            has_body_content = block is not None and (
                block["variants"] or block["protein_fat"]
                or block["description_lines"] or block["components_lines"]
            )
            if has_body_content or (block is not None and not collecting_header):
                flush_block()
                block = new_block(current_animal)
            elif block is None:
                block = new_block(current_animal)

            if FLAVOR_SUFFIX_RE.match(line):
                life_part, flavor_part = "", line
            else:
                life_part, flavor_part = split_header_line(line)
            if life_part:
                block["life_stage_parts"].append(life_part)
            if flavor_part:
                block["flavor_parts"].append(flavor_part)
            collecting_header = True
            continue

        if block is None:
            block = new_block(current_animal)
        if block["components_lines"]:
            block["components_lines"].append(line)
        else:
            block["description_lines"].append(line)

    flush_block()
    return products


def clean_bundle_life_stage(text):
    """
    Cleans a multipack's life-stage header text, e.g. "ADULT 5+1 ΣΕ ΣΑΛΤΣΑ"
    -> "Adult (in Gravy)". The "5+1"-style promo quantity is dropped (it is
    already reflected in the variant's total weight), and a trailing
    "σε σάλτσα"/"σε ζελέ" is converted into a "(in Gravy)"/"(in Jelly)" suffix
    that applies to the whole pack.
    """
    suffix = ""
    if re.search(r'σε\s+σ[αά]λτσα', text, re.IGNORECASE):
        suffix = " (in Gravy)"
    elif re.search(r'σε\s+ζ[εέ]λ[εέ]', text, re.IGNORECASE):
        suffix = " (in Jelly)"
    text = re.sub(r'σε\s+σ[αά]λτσα|σε\s+ζ[εέ]λ[εέ]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\d+\s*\+\s*\d+', '', text)
    life_stage = clean_life_stage(text)
    return (life_stage + suffix).strip()


def build_bundle_name(block):
    life_stage = clean_bundle_life_stage(" ".join(block["life_stage_parts"]))
    flavor_summary = build_bundle_flavor_summary(block["description_lines"])
    base = f"{life_stage} Multipack" if life_stage else "Multipack"
    name = f"{base} - {flavor_summary}" if flavor_summary else base
    return fix_greek_accents(name)


def build_name(block):
    if block.get("is_bundle"):
        return build_bundle_name(block)
    life_stage = clean_life_stage(" ".join(block["life_stage_parts"]))
    flavor = clean_flavor(" ".join(block["flavor_parts"]))
    parts = [p for p in (life_stage, flavor) if p]
    name = " - ".join(parts) if parts else None
    return fix_greek_accents(name) if name else None


def classify_category_name(block):
    if block.get("is_bundle"):
        return "Bundle"
    flavor_text = " ".join(block["flavor_parts"]).lower()
    if "σάλτσα" in flavor_text or "ζελέ" in flavor_text:
        return "Sachets"
    return "Dry Food"


class Command(BaseCommand):
    help = "Imports CLUB4PAWS products from the 'OLA TA KEIMENA.docx' catalog file."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", required=True,
            help="Full path to the OLA TA KEIMENA.docx file.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Parse and print a summary without writing to the database.",
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        dry_run = options["dry_run"]

        try:
            company = Company.objects.get(name="CLUB4PAWS")
        except Company.DoesNotExist:
            raise CommandError(
                "Company 'CLUB4PAWS' not found. Run 'python manage.py seed_data' first."
            )

        try:
            blocks = parse_document(file_path)
        except Exception as exc:
            raise CommandError(f"Failed to read/parse the document: {exc}")

        seen_skus = set()
        created_products = 0
        updated_products = 0
        created_variants = 0
        skipped_no_variant = 0

        for block in blocks:
            if not block["variants"]:
                skipped_no_variant += 1
                continue

            name_en = build_name(block)
            if not name_en:
                skipped_no_variant += 1
                continue

            category_name = classify_category_name(block)
            category = Category.objects.get(name=category_name)
            animal_type = AnimalType.objects.get(name=block["animal"])

            from products.models import generate_ascii_slug
            from products.name_i18n import translate_product_name_to_greek

            name = translate_product_name_to_greek(
                name_en,
                animal_slug=animal_type.slug,
                slug=generate_ascii_slug(name_en),
                category_slug=category.slug,
            )

            is_bundle = block.get("is_bundle", False)
            bundle_contents = ""
            if is_bundle:
                description = build_bundle_description(block["description_lines"])
                components = ""
                bundle_contents = build_bundle_flavor_summary(block["description_lines"])
            else:
                description = " ".join(block["description_lines"]).strip()
                components_parts = []
                if block["protein_fat"]:
                    components_parts.append(block["protein_fat"])
                components_parts.extend(block["components_lines"])
                components = " ".join(components_parts).strip()

            if dry_run:
                tag = " [BUNDLE]" if is_bundle else ""
                self.stdout.write(f"[DRY RUN] Would import: {name} ({category_name}, {len(block['variants'])} variants){tag}")
                continue

            product, was_created = Product.objects.get_or_create(
                name=name,
                company=company,
                defaults={
                    "animal_type": animal_type,
                    "category": category,
                    "description": description,
                    "components": components,
                    "bundle_contents": bundle_contents,
                },
            )
            if was_created:
                created_products += 1
            else:
                updated_products += 1

            for variant_data in block["variants"]:
                sku = variant_data["sku"]
                if sku in KNOWN_DUPLICATE_SKUS:
                    if sku in seen_skus:
                        sku = None  # Avoid a uniqueness conflict; see module docstring.
                    else:
                        seen_skus.add(sku)

                _, variant_created = ProductVariant.objects.get_or_create(
                    product=product,
                    weight=variant_data["weight_kg"],
                    defaults={
                        "sku": sku,
                        "price": variant_data["price"],
                        "stock": 0,
                    },
                )
                if variant_created:
                    created_variants += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Products created: {created_products}, already existed: {updated_products}, "
            f"variants created: {created_variants}, blocks skipped (no usable data): {skipped_no_variant}"
        ))
