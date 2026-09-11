"""
Meaning-based Greek product titles for the storefront.

Subject first, then category, optional brand line, then audience:
  adult-all-breeds-beef-in-jelly (dog, sachets)
    → «Βοδινό σε ζελέ φακελάκι - για ενήλικους σκύλους κάθε ράτσας»
  classic-adult-duck (dog, dry-food)
    → «Πάπια ξηρά τροφή Classic - για ενήλικους σκύλους»
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from products.management.commands.import_club4paws import GREEK_ACCENT_FIXES

_CATEGORY_WORD = {
    "dry-food": "ξηρά τροφή",
    "canned-food": "κονσέρβα",
    "sachets": "φακελάκι",
    "litter": "άμμος",
    "bundle": "πολυσυσκευασία",
}

_SERIES = frozenset({"classic", "ultra", "derma", "original", "complet"})

_FLAVOR = {
    "chicken": "Κοτόπουλο",
    "beef": "Βοδινό",
    "lamb": "Αρνί",
    "salmon": "Σολομός",
    "turkey": "Γαλοπούλα",
    "duck": "Πάπια",
    "rabbit": "Κουνέλι",
    "fish": "Ψάρι",
    "mackerel": "Σκουμπρί",
    "tuna": "Τόνος",
    "goat": "Κατσίκι",
    "rice": "Ρύζι",
    "potatoes": "Πατάτες",
    "potato": "Πατάτα",
    "catnip": "γατόχορτο",
    "arni": "Αρνί",
    "bodino": "Βοδινό",
    "solomos": "Σολομός",
    "solouos": "Σολομός",
    "kotopoulo": "Κοτόπουλο",
    "kotopoulou": "Κοτόπουλου",
    "galopoula": "Γαλοπούλα",
    "papia": "Πάπια",
    "elaphi": "Ελάφι",
    "sukoti": "Συκώτι",
    "kardies": "Καρδιές",
    "tono": "Τόνος",
    "mprokolo": "Μπρόκολο",
    "kolokutha": "Κολοκύθα",
    "lakhano": "Λάχανο",
    "arakas": "Αρακάς",
    "karota": "Καρότα",
    "glukopatata": "Γλυκοπατάτα",
    "agriokhoiros": "Αγριόχοιρος",
    "pate": "πατέ",
    "kokkines": "Κόκκινες",
    "piperies": "Πιπεριές",
    "bodinou": "Βοδινού",
}

_GREEK_TITLE_FIXES: list[tuple[str, str]] = [
    (r"\bΑρνι\b", "Αρνί"),
    (r"\bΒοδινο\b", "Βοδινό"),
    (r"\bΣυκωτι\b", "Συκώτι"),
    (r"\bΒοδινου\b", "Βοδινού"),
    (r"\bΕλαφι\b", "Ελάφι"),
    (r"\bΚοτοπουλο\b", "Κοτόπουλο"),
    (r"\bΚοτοπουλου\b", "Κοτόπουλου"),
    (r"\bΣολομος\b", "Σολομός"),
    (r"\bΠαπια\b", "Πάπια"),
    (r"\bΓαλοπουλα\b", "Γαλοπούλα"),
    (r"\bΧαμομηλι\b", "Χαμομήλι"),
    (r"\bΜελισσοχορτο\b", "Μελισσόχορτο"),
    (r"\bΚαρδιες\b", "Καρδιές"),
    (r"\bΜπροκολο\b", "Μπρόκολο"),
    (r"\bΚολοκυθα\b", "Κολοκύθα"),
    (r"\bΛαχανο\b", "Λάχανο"),
    (r"\bΑρακας\b", "Αρακάς"),
    (r"\bΓλυκοπατατα\b", "Γλυκοπατάτα"),
    (r"\bΚατσικι\b", "Κατσίκι"),
    (r"\bφυλών\b", "ρατσών"),
    (r"\bφυλές\b", "ράτσες"),
    (r"\bφυλή\b", "ράτσα"),
    (r"Όλες οι ράτσες", "κάθε ράτσας"),
    (r"όλες οι ράτσες", "κάθε ράτσας"),
    (r"\bµε\b", "με"),
    (r"\bΣε Σάλτσα\b", "σε σάλτσα"),
    (r"\bσε Σάλτσα\b", "σε σάλτσα"),
    (r"\bΣε Ζελέ\b", "σε ζελέ"),
    (r"(?<=\S) Και (?=\S)", " και "),
    (r"(?<=\S) Με (?=\S)", " με "),
    (r"\s*&\s*", " και "),
    (r"\bμε Τόνος\b", "με Τόνο"),
]

_ALLOWED_LATIN = frozenset(
    {
        "classic",
        "ultra",
        "derma",
        "original",
        "complet",
        "junior",
        "puppy",
        "senior",
        "salmon",
        "ageing",
        "mature",
        "young",
        "light",
        "energy",
        "active",
        "mini",
        "medium",
        "maxi",
        "large",
        "small",
        "indoor",
        "x",
        "ocean",
        "life",
        "savoury",
        "medleys",
        "duo",
        "protein",
        "hunter",
        "african",
        "sunset",
        "deep",
        "forest",
        "canadian",
        "whitewaters",
        "nomad",
        "wings",
        "cover",
        "extra",
        "strong",
        "clumping",
        "multiple",
        "cat",
        "litterfree",
        "paws",
        "multi",
        "crystals",
        "fast",
        "acting",
        "odour",
        "odor",
        "control",
        "spring",
        "garden",
        "lavender",
        "total",
        "g",
    }
)

# Catalogue lines the slug parser cannot reconstruct (flavors live in the DESC).
SLUG_TITLE_OVERRIDES: dict[str, str] = {
    "puppy-original-dog": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - για κουτάβια"
    ),
    "puppy-ocean-dog": (
        "Σολομός ξηρά τροφή Ocean - για κουτάβια μικρόσωμων/μεσαίων ρατσών"
    ),
    "puppy-large-original-dog": (
        "Κοτόπουλο ξηρά τροφή Original - για κουτάβια μεγαλόσωμων ρατσών"
    ),
    "adult-original-dog": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - για ενήλικους σκύλους"
    ),
    "adult-lamb-dog": (
        "Αρνί ξηρά τροφή - για ενήλικους σκύλους με διατροφική ευαισθησία"
    ),
    "adult-ocean-dog": (
        "Σολομός και Τόνος ξηρά τροφή Ocean - για ενήλικους σκύλους"
    ),
    "adult-large-original-dog": (
        "Κοτόπουλο ξηρά τροφή Original - για ενήλικους σκύλους μεγαλόσωμων ρατσών"
    ),
    "adult-small-original-dog": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - "
        "για ενήλικους σκύλους μικρόσωμων ρατσών"
    ),
    "adult-small-lamb-dog": (
        "Αρνί ξηρά τροφή - για ενήλικους σκύλους μικρόσωμων ρατσών"
    ),
    "adult-small-ocean-dog": (
        "Σολομός και Τόνος ξηρά τροφή Ocean - "
        "για ενήλικους σκύλους μικρόσωμων ρατσών"
    ),
    "adult-small-low-fat-dog": (
        "Γαλοπούλα ξηρά τροφή Light - για ενήλικους σκύλους μικρόσωμων ρατσών"
    ),
    "active-life-dog": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Active Life - για δραστήριους σκύλους"
    ),
    "senior-original-dog": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - για ηλικιωμένους σκύλους"
    ),
    "adult-low-fat-dog": "Γαλοπούλα ξηρά τροφή Light - για ενήλικους σκύλους",
    "kitten-cat": "Γαλοπούλα και Κοτόπουλο ξηρά τροφή - για γατάκια",
    "adult-original-cat": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - για ενήλικες γάτες"
    ),
    "adult-ocean-cat": "Σολομός και Τόνος ξηρά τροφή Ocean - για ενήλικες γάτες",
    "sterilised-original-cat": (
        "Γαλοπούλα και Κοτόπουλο ξηρά τροφή Original - για στειρωμένες γάτες"
    ),
    "sterilised-ocean-cat": "Σολομός ξηρά τροφή Ocean - για στειρωμένες γάτες",
    "kitten-pate-kotopoulo-ue-tono": (
        "Κοτόπουλο με Τόνο πατέ κονσέρβα - για γατάκια"
    ),
    "single-protein-7876340": (
        "Κοτόπουλο με Πάπια και Καρότα κονσέρβα Duo Protein - για ενήλικους σκύλους"
    ),
    "single-protein-7876350": (
        "Γαλοπούλα με Κατσίκι και Γλυκοπατάτα κονσέρβα Duo Protein - "
        "για ενήλικους σκύλους"
    ),
    "single-protein-7876360": (
        "Κοτόπουλο και Γαλοπούλα με Κολοκύθα κονσέρβα Puppy Original - για κουτάβια"
    ),
}


@dataclass
class ParsedSlug:
    series: list[str] = field(default_factory=list)
    life: str | None = None
    size: str | None = None
    breed_scope: str | None = None
    traits: list[str] = field(default_factory=list)
    multipack: bool = False
    flavor_tokens: list[str] = field(default_factory=list)


def _fix_accents_preserve_case(text: str) -> str:
    def replacer(right: str):
        def _repl(match: re.Match[str]) -> str:
            original = match.group(0)
            if original[:1].isupper():
                return right[:1].upper() + right[1:]
            return right

        return _repl

    result = text
    for wrong, right in GREEK_ACCENT_FIXES.items():
        result = re.sub(
            rf"\b{re.escape(wrong)}\b",
            replacer(right),
            result,
            flags=re.IGNORECASE,
        )
    return result


def _polish(name: str) -> str:
    result = (name or "").replace("\u00b5", "μ").replace("\u03bc", "μ")
    result = _fix_accents_preserve_case(result)
    for pattern, repl in _GREEK_TITLE_FIXES:
        result = re.sub(pattern, repl, result)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s*,\s*", ", ", result)
    result = re.sub(r"\s*-\s*[Γγ]ια\s+", " - για ", result)
    if result:
        result = result[0].upper() + result[1:]
    return result.strip(" -")


def _slug_tokens(slug: str) -> list[str]:
    text = (slug or "").strip().lower()
    text = text.replace("mediumlarge", "medium-large")
    text = text.replace("4-in-1", "4in1")
    return [t for t in text.split("-") if t]


def parse_product_slug(slug: str, animal_slug: str) -> ParsedSlug:
    tokens = _slug_tokens(slug)
    parsed = ParsedSlug()
    i = 0

    if tokens and tokens[-1] in {"dog", "cat"} and tokens[-1] == animal_slug:
        tokens = tokens[:-1]

    series_labels = {
        "classic": "Classic",
        "ultra": "Ultra",
        "derma": "Derma",
        "original": "Original",
        "complet": "Complet",
        "ocean": "Ocean",
    }

    while i < len(tokens):
        tok = tokens[i]

        if tok == "savoury" and i + 1 < len(tokens) and tokens[i + 1] == "medleys":
            parsed.series.append("Savoury Medleys")
            i += 2
            continue

        if tok == "active" and i + 1 < len(tokens) and tokens[i + 1] == "life":
            parsed.series.append("Active Life")
            parsed.traits.append("Active")
            i += 2
            continue

        if tok == "low" and i + 1 < len(tokens) and tokens[i + 1] == "fat":
            parsed.traits.append("Light")
            i += 2
            continue

        if tok in series_labels:
            parsed.series.append(series_labels[tok])
            i += 1
            continue

        if tok in {"multipack", "bundle"}:
            parsed.multipack = True
            i += 1
            continue

        if tok in {
            "adult",
            "puppy",
            "puppies",
            "kitten",
            "junior",
            "senior",
            "ageing",
            "mature",
            "young",
        }:
            parsed.life = tok
            i += 1
            continue

        if tok in {"mini", "medium", "maxi"} and parsed.breed_scope is None:
            if i + 1 < len(tokens) and tokens[i + 1] == "breeds":
                parsed.breed_scope = tok
                i += 2
                continue
            if i + 1 < len(tokens) and tokens[i + 1] == "large":
                parsed.breed_scope = "mediumlarge"
                i += 2
                continue
            parsed.size = {"mini": "Mini", "medium": "Medium", "maxi": "Maxi"}[tok]
            i += 1
            continue

        if tok in {"small", "large"}:
            if i + 1 < len(tokens) and tokens[i + 1] == "breeds":
                parsed.breed_scope = tok
                i += 2
                continue
            parsed.breed_scope = tok
            i += 1
            continue

        if tok == "all" and i + 1 < len(tokens) and tokens[i + 1] == "breeds":
            parsed.breed_scope = "all"
            i += 2
            continue

        if tok == "breeds":
            i += 1
            continue

        if tok in {"light", "energy", "active"}:
            parsed.traits.append("Light" if tok == "light" else tok.capitalize())
            i += 1
            continue

        if tok in {"sterilized", "sterilised"}:
            parsed.traits.append("sterilized")
            i += 1
            continue

        if tok == "hairball":
            parsed.traits.append("hairball")
            i += 1
            if i < len(tokens) and tokens[i] == "control":
                parsed.traits.append("control")
                i += 1
            continue

        if tok == "sensitive" and i + 1 < len(tokens) and tokens[i + 1] == "digestion":
            parsed.traits.append("sensitive")
            i += 2
            continue

        if tok == "urinary" and i + 1 < len(tokens) and tokens[i + 1] == "health":
            parsed.traits.append("urinary")
            i += 2
            continue

        if tok == "daily" and i + 1 < len(tokens) and tokens[i + 1] == "care":
            parsed.traits.append("daily_care")
            i += 2
            continue

        if tok == "indoor":
            parsed.traits.append("indoor")
            i += 1
            if i < len(tokens) and tokens[i] in {"4in1", "4"}:
                i += 1
                parsed.traits.append("4in1")
            continue

        if tok == "for" and i + 1 < len(tokens) and tokens[i + 1] == "cats":
            parsed.traits.append("cats7")
            i += 2
            if i < len(tokens) and tokens[i] in {"7", "7+"}:
                i += 1
            continue

        if tok in {"7", "7+"}:
            if "cats7" not in parsed.traits:
                parsed.traits.append("cats7")
            i += 1
            continue

        if tok == "single" and i + 1 < len(tokens) and tokens[i + 1] == "protein":
            parsed.series.append("Μονοπρωτεϊνική")
            i += 2
            continue

        if tok == "in" and i + 1 < len(tokens) and tokens[i + 1] in {"gravy", "jelly"}:
            parsed.flavor_tokens.append(f"in-{tokens[i + 1]}")
            i += 2
            continue

        if tok in {"and", "with", "kai", "ue"}:
            parsed.flavor_tokens.append("and" if tok in {"and", "kai"} else "with")
            i += 1
            continue

        if tok == "se" and i + 1 < len(tokens) and tokens[i + 1] in {
            "saltsa",
            "zele",
            "gravy",
            "jelly",
        }:
            sauce = tokens[i + 1]
            parsed.flavor_tokens.append(
                "in-gravy" if sauce in {"saltsa", "gravy"} else "in-jelly"
            )
            i += 2
            continue

        if re.fullmatch(r"\d+x", tok) or tok in _FLAVOR or tok in {"gravy", "jelly"}:
            parsed.flavor_tokens.append(tok)
            i += 1
            continue

        if re.fullmatch(r"\d+", tok):
            parsed.flavor_tokens.append(tok)
            i += 1
            continue

        parsed.flavor_tokens.append(tok)
        i += 1

    return parsed


def _breed_phrase(scope: str | None) -> str:
    return {
        "all": "κάθε ράτσας",
        "small": "μικρόσωμων ρατσών",
        "medium": "μεσαίων ρατσών",
        "large": "μεγαλόσωμων ρατσών",
        "mediumlarge": "μεσαίων/μεγαλόσωμων ρατσών",
    }.get(scope or "", "")


def _animal_noun(animal: str, plural: bool = True) -> str:
    if animal == "cat":
        return "γάτες" if plural else "γάτα"
    return "σκύλους" if plural else "σκύλο"


def _audience(parsed: ParsedSlug, animal: str) -> str:
    breed = _breed_phrase(parsed.breed_scope)
    is_cat = animal == "cat"
    traits = set(parsed.traits)

    if "cats7" in traits:
        return "γάτες 7+"
    if "urinary" in traits:
        return (
            "γάτες με ευαίσθητο ουροποιητικό"
            if is_cat
            else "σκύλους με ευαίσθητο ουροποιητικό"
        )
    if "sensitive" in traits:
        return f"{'γάτες' if is_cat else 'σκύλους'} με ευαίσθητο πεπτικό"
    if "hairball" in traits:
        return "γάτες με τριχόμπαλες" if is_cat else "σκύλους"
    if "indoor" in traits:
        return "γάτες"
    if "daily_care" in traits:
        return (
            f"ενήλικες {_animal_noun(animal)}"
            if is_cat
            else f"ενήλικους {_animal_noun(animal)}"
        )

    sterilized = "sterilized" in traits
    life = parsed.life

    if life in {"puppy", "puppies", "junior"}:
        who = "στειρωμένα κουτάβια" if sterilized else "κουτάβια"
        return f"{who} {breed}".strip() if breed else who

    if life == "kitten":
        return "στειρωμένα γατάκια" if sterilized else "γατάκια"

    if life in {"senior", "ageing", "mature"}:
        if is_cat:
            who = "ηλικιωμένες στειρωμένες γάτες" if sterilized else "ηλικιωμένες γάτες"
        else:
            who = (
                "ηλικιωμένους στειρωμένους σκύλους"
                if sterilized
                else "ηλικιωμένους σκύλους"
            )
        return f"{who} {breed}".strip() if breed else who

    if life == "young":
        if is_cat:
            return "νεαρές στειρωμένες γάτες" if sterilized else "νεαρές γάτες"
        return "νεαρούς στειρωμένους σκύλους" if sterilized else "νεαρούς σκύλους"

    if sterilized:
        who = "στειρωμένες γάτες" if is_cat else "στειρωμένους σκύλους"
    elif life == "adult" or life is None:
        who = "ενήλικες γάτες" if is_cat else "ενήλικους σκύλους"
    else:
        who = _animal_noun(animal)

    return f"{who} {breed}".strip() if breed else who


def _line_modifiers(parsed: ParsedSlug) -> list[str]:
    mods: list[str] = []
    for trait in parsed.traits:
        low = trait.lower()
        if low in {"light", "energy", "active"}:
            mods.append("Light" if low == "light" else trait.capitalize())
    return mods


def _format_flavor(tokens: list[str]) -> str:
    if not tokens:
        return ""

    parts: list[str] = []
    prev_was_flavor = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in {"in-gravy", "gravy"}:
            parts.append("σε σάλτσα")
            prev_was_flavor = False
            i += 1
            continue
        if tok in {"in-jelly", "jelly"}:
            parts.append("σε ζελέ")
            prev_was_flavor = False
            i += 1
            continue
        if tok == "and":
            parts.append("και")
            prev_was_flavor = False
            i += 1
            continue
        if tok == "with":
            parts.append("με")
            prev_was_flavor = False
            i += 1
            continue
        if tok in _FLAVOR:
            if prev_was_flavor and tok != "piperies":
                parts.append("και")
            parts.append(_FLAVOR[tok])
            prev_was_flavor = True
            i += 1
            continue
        if re.fullmatch(r"\d+x", tok, re.I):
            if parts:
                parts.append(",")
            parts.append(tok.lower())
            prev_was_flavor = False
            i += 1
            continue
        if re.fullmatch(r"\d+", tok):
            parts.append(tok)
            prev_was_flavor = False
            i += 1
            continue
        i += 1

    text = " ".join(parts)
    text = re.sub(r"\s+,", ",", text)
    text = re.sub(r",\s*", ", ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.lstrip(", ").strip()
    sauce = ""
    for marker in (" σε σάλτσα", " σε ζελέ"):
        if text.endswith(marker):
            sauce = marker
            text = text[: -len(marker)].strip()
            break
    if "," not in text and " και " in text:
        items = [p.strip() for p in text.split(" και ") if p.strip()]
        if len(items) == 2:
            text = f"{items[0]} και {items[1]}"
        elif len(items) > 2:
            text = ", ".join(items[:-1]) + " και " + items[-1]
    return (text + sauce).strip(" ,")


def _brand_bits(parsed: ParsedSlug) -> str:
    bits: list[str] = []
    bits.extend(parsed.series)
    if parsed.size:
        bits.append(parsed.size)
    series_blob = " ".join(parsed.series).lower()
    for mod in _line_modifiers(parsed):
        if mod.lower() not in series_blob:
            bits.append(mod)
    if "indoor" in parsed.traits:
        bits.append("Indoor 4 σε 1" if "4in1" in parsed.traits else "Indoor")
    return " ".join(bits).strip()


def _category_word(category_slug: str, *, multipack: bool = False) -> str:
    if multipack:
        return "πολυσυσκευασία"
    return _CATEGORY_WORD.get((category_slug or "").lower(), "")


def _assemble_title(
    *,
    flavor: str,
    category_slug: str,
    brand: str,
    audience: str,
    multipack: bool = False,
) -> str:
    cat = _category_word(category_slug, multipack=multipack)
    flavor_l = (flavor or "").lower()
    if cat and flavor_l and cat.lower() in flavor_l:
        cat = ""
    head: list[str] = []
    if flavor:
        head.append(flavor)
    if cat:
        head.append(cat)
    if brand:
        head.append(brand)
    subject = " ".join(head).strip()
    if not subject:
        subject = cat or _category_word(category_slug, multipack=multipack) or "Τροφή"
    return f"{subject} - για {audience}"


def build_meaning_title(
    slug: str,
    animal_slug: str,
    current_name: str = "",
    category_slug: str = "",
) -> str:
    """Build subject-first Greek title from slug + animal + category."""
    animal = (animal_slug or "").lower()
    if animal not in {"dog", "cat"}:
        animal = "dog"

    override = SLUG_TITLE_OVERRIDES.get((slug or "").strip().lower())
    if override:
        return _polish(override)

    current = (current_name or "").strip()
    already_structured = (
        " - για " in current.lower() and not re.search(r"\((Dog|Cat)\)", current)
    )
    if already_structured or (
        (category_slug or "").lower() == "litter" and current
    ):
        return _polish_existing_greek(
            current,
            animal_slug=animal,
            category_slug=category_slug,
        )

    tokens = _slug_tokens(slug)
    englishish = any(
        t in {
            "adult",
            "puppy",
            "puppies",
            "kitten",
            "junior",
            "senior",
            "chicken",
            "classic",
            "ultra",
            "sterilized",
            "sterilised",
            "breeds",
            "multipack",
            "light",
            "derma",
            "original",
            "single",
            "protein",
            "hairball",
            "urinary",
            "sensitive",
            "indoor",
            "ageing",
            "mature",
            "young",
            "energy",
            "active",
            "complet",
            "lamb",
            "salmon",
            "turkey",
            "beef",
            "duck",
            "rabbit",
            "fish",
            "savoury",
            "ocean",
            "tuna",
        }
        for t in tokens
    )

    if not englishish:
        return _polish_existing_greek(
            current or slug,
            animal_slug=animal,
            category_slug=category_slug,
        )

    parsed = parse_product_slug(slug, animal)
    return _polish(
        _assemble_title(
            flavor=_format_flavor(parsed.flavor_tokens),
            category_slug=category_slug,
            brand=_brand_bits(parsed),
            audience=_audience(parsed, animal),
            multipack=parsed.multipack,
        )
    )


def _polish_existing_greek(
    name: str,
    *,
    animal_slug: str = "",
    category_slug: str = "",
) -> str:
    text = (name or "").strip()
    if not text:
        return text

    if " - για " in text.lower():
        return _polish(text)

    animal = (animal_slug or "dog").lower()
    default_audience = "ενήλικες γάτες" if animal == "cat" else "ενήλικους σκύλους"
    if (category_slug or "").lower() == "litter":
        default_audience = (
            "ηλικιωμένες γάτες" if re.search(r"senior", text, re.I) else "γάτες"
        )

    medley = re.match(r"^Savoury Medleys\s*[-–—]\s*(.+)$", text, re.I)
    if medley:
        return _polish(
            _assemble_title(
                flavor=medley.group(1).strip(),
                category_slug=category_slug,
                brand="Savoury Medleys",
                audience=default_audience,
            )
        )

    if "·" in text:
        left, right = [p.strip() for p in text.split("·", 1)]
        brand = ""
        audience = left
        mono = re.match(r"^(Μονοπρωτεϊνική)\s*(.*)$", left, flags=re.IGNORECASE)
        if mono:
            brand = "Μονοπρωτεϊνική"
            audience = mono.group(2).strip()
        audience = re.sub(r"^[Γγ]ια\s+", "", audience).strip() or default_audience
        for token in ("Classic", "Ultra", "Derma", "Original", "Light", "Energy", "Active"):
            if audience.startswith(token):
                brand = f"{brand} {token}".strip() if brand else token
                audience = audience[len(token) :].strip()
                audience = re.sub(r"^[Γγ]ια\s+", "", audience).strip()
        return _polish(
            _assemble_title(
                flavor=right,
                category_slug=category_slug,
                brand=brand,
                audience=audience or default_audience,
            )
        )

    if re.match(r"^[Γγ]ια\s+", text):
        audience = re.sub(r"^[Γγ]ια\s+", "", text).strip()
        return _polish(
            _assemble_title(
                flavor="",
                category_slug=category_slug,
                brand="",
                audience=audience,
            )
        )

    return _polish(
        _assemble_title(
            flavor=text,
            category_slug=category_slug,
            brand="",
            audience=default_audience,
        )
    )


def translate_product_name_to_greek(
    name: str,
    *,
    animal_slug: str = "",
    slug: str = "",
    category_slug: str = "",
) -> str:
    if slug and animal_slug:
        return build_meaning_title(
            slug,
            animal_slug,
            current_name=name,
            category_slug=category_slug,
        )
    return _polish_existing_greek(
        name or "",
        animal_slug=animal_slug,
        category_slug=category_slug,
    )


def needs_greek_translation(name: str) -> bool:
    if not name:
        return False
    if " - για " not in name.lower():
        return True
    if re.search(r"φυλ", name, flags=re.IGNORECASE):
        return True
    if "·" in name:
        return True
    if re.match(r"^[Γγ]ια\s+", name):
        return True
    for word in re.findall(r"[A-Za-z]+", name):
        if word.lower() not in _ALLOWED_LATIN:
            return True
    if re.match(r"^(Ενήλικες|Κουτάβια|Γατάκι|Στειρωμένα)\b", name):
        return True
    return False
