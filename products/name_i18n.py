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
    "rice": "Ρύζι",
    "potatoes": "Πατάτες",
    "potato": "Πατάτα",
    "catnip": "γατόχορτο",
    "arni": "Αρνί",
    "bodino": "Βοδινό",
    "solomos": "Σολομός",
    "kotopoulo": "Κοτόπουλο",
    "galopoula": "Γαλοπούλα",
    "papia": "Πάπια",
    "elaphi": "Ελάφι",
    "sukoti": "Συκώτι",
    "kardies": "Καρδιές",
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
    (r"\bφυλών\b", "ρατσών"),
    (r"\bφυλές\b", "ράτσες"),
    (r"\bφυλή\b", "ράτσα"),
    (r"Όλες οι ράτσες", "κάθε ράτσας"),
    (r"όλες οι ράτσες", "κάθε ράτσας"),
    (r"\bµε\b", "με"),
    (r"(?<=\S) Και (?=\S)", " και "),
    (r"(?<=\S) Με (?=\S)", " με "),
]

_ALLOWED_LATIN = frozenset(
    {
        "classic",
        "ultra",
        "derma",
        "original",
        "complet",
        "junior",
        "senior",
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
    }
)


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
    result = _fix_accents_preserve_case(name)
    for pattern, repl in _GREEK_TITLE_FIXES:
        result = re.sub(pattern, repl, result)
    result = re.sub(r"\s{2,}", " ", result)
    result = re.sub(r"\s*-\s*", " - ", result)
    result = re.sub(r"\s*,\s*", ", ", result)
    result = re.sub(r"\s+&\s+", " & ", result)
    result = re.sub(r"\s*-\s*Για\s+", " - για ", result)
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
    }

    while i < len(tokens):
        tok = tokens[i]

        if tok in _SERIES:
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

        if tok in {"and", "with"}:
            parsed.flavor_tokens.append(tok)
            i += 1
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
        if tok in {"and", "with"}:
            parts.append("και")
            prev_was_flavor = False
            i += 1
            continue
        if tok in _FLAVOR:
            if prev_was_flavor:
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
    text = re.sub(r"^(.+?) και (.+?) και (.+)$", r"\1, \2 και \3", text)
    return text.strip(" ,")


def _brand_bits(parsed: ParsedSlug) -> str:
    bits: list[str] = []
    bits.extend(parsed.series)
    if parsed.size:
        bits.append(parsed.size)
    bits.extend(_line_modifiers(parsed))
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
    head: list[str] = []
    if flavor:
        head.append(flavor)
    if cat:
        head.append(cat)
    if brand:
        head.append(brand)
    subject = " ".join(head).strip()
    if not subject:
        subject = cat or "Τροφή"
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
        }
        for t in tokens
    )

    if not englishish:
        return _polish_existing_greek(
            current_name or slug,
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
