"""
Smart storefront search: synonyms, Greeklish, popular misspellings.

Maps everyday Greek / Latin / Greeklish queries onto animal, category,
brand, and free-text matches across product fields. Results are ordered
by Favourite.score (then name).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from django.db.models import Q, QuerySet

from products.catalog import get_catalog_queryset
from products.models import Product

# Live dropdown size — broad queries (e.g. «σκύλος») need a useful list.
SEARCH_SUGGESTION_LIMIT = 12

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^0-9a-zα-ωάέήίόύώϊϋΐΰ]+", re.IGNORECASE)

_GREEK_TO_LATIN = (
    ("ου", "ou"),
    ("αυ", "au"),
    ("ευ", "eu"),
    ("αι", "ai"),
    ("ει", "ei"),
    ("οι", "oi"),
    ("υι", "yi"),
    ("μπ", "b"),
    ("ντ", "d"),
    ("γκ", "g"),
    ("τσ", "ts"),
    ("τζ", "tz"),
    ("θ", "th"),
    ("χ", "ch"),
    ("ψ", "ps"),
    ("α", "a"),
    ("β", "v"),
    ("γ", "g"),
    ("δ", "d"),
    ("ε", "e"),
    ("ζ", "z"),
    ("η", "i"),
    ("ι", "i"),
    ("κ", "k"),
    ("λ", "l"),
    ("μ", "m"),
    ("ν", "n"),
    ("ξ", "x"),
    ("ο", "o"),
    ("π", "p"),
    ("ρ", "r"),
    ("σ", "s"),
    ("ς", "s"),
    ("τ", "t"),
    ("υ", "y"),
    ("φ", "f"),
    ("ω", "o"),
)


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def to_greeklish(value: str) -> str:
    text = strip_accents(value).lower()
    for src, dst in _GREEK_TO_LATIN:
        text = text.replace(src, dst)
    return text


def normalize_query(value: str) -> str:
    """Lowercase, strip accents, keep letters/digits/spaces only."""
    text = strip_accents(value or "").lower().replace("ς", "σ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


@dataclass
class SearchIntent:
    """Structured meaning extracted from a user query."""

    animals: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    companies: set[str] = field(default_factory=set)
    # Each inner set is OR'd (synonyms); groups are AND'd together.
    text_groups: list[set[str]] = field(default_factory=list)


def _merge_intent(target: SearchIntent, payload: dict) -> None:
    target.animals.update(payload.get("animals", ()))
    target.categories.update(payload.get("categories", ()))
    target.companies.update(payload.get("companies", ()))
    terms = {t for t in payload.get("text_terms", ()) if t}
    if terms:
        target.text_groups.append(terms)


# Alias catalogue: (aliases…, intent). Matching also auto-adds Greeklish keys.
_ALIAS_ROWS: list[tuple[tuple[str, ...], dict]] = [
    # Animals
    (
        (
            "σκυλοσ",
            "σκυλου",
            "σκυλοι",
            "σκυλο",
            "dog",
            "dogs",
            "skylos",
            "skilos",
            "skyloi",
            "σκυλοτροφη",
            "skilotrofi",
            "skilotrofh",
            "dog food",
        ),
        {"animals": {"dog"}},
    ),
    (
        (
            "γατα",
            "γατασ",
            "γατεσ",
            "γατι",
            "cat",
            "cats",
            "gata",
            "gates",
            "γατοτροφη",
            "gatotrofi",
            "gatotrofh",
            "cat food",
        ),
        {"animals": {"cat"}},
    ),
    # Categories
    (
        (
            "ξηρα τροφη",
            "ξηρη τροφη",
            "ξηρεσ τροφεσ",
            "χυμα ξηρα τροφη",
            "χυμα",
            "ξηρα",
            "ξηρη",
            "dry food",
            "xira trofi",
            "xiri trofi",
            "xira",
            "xuma trofi",
            "xuma",
            "kibble",
        ),
        {"categories": {"dry-food"}},
    ),
    (
        (
            "κονσερβεσ",
            "κονσερβα",
            "κονσερβ",
            "πατε",
            "pate",
            "canned",
            "canned food",
            "wet food",
            "υγρα τροφη",
            "konserves",
            "konserva",
        ),
        {"categories": {"canned-food"}},
    ),
    (
        (
            "φακελακια",
            "φακελακι",
            "φακελοσ",
            "sachets",
            "sachet",
            "pouch",
            "pouches",
            "fikelakia",
            "fakelakia",
            "fakelaki",
        ),
        {"categories": {"sachets"}},
    ),
    (
        (
            "αμμοσ",
            "αμοσ",
            "αμμοσ γατασ",
            "litter",
            "cat litter",
            "ammos",
            "amos",
        ),
        {"categories": {"litter"}},
    ),
    (
        (
            "bundle",
            "bundles",
            "πακετο",
            "πακετα",
            "πακετο προσφορασ",
            "πακετα προσφορασ",
            "προσφορα",
            "προσφορεσ",
            "paketo",
            "paketa",
        ),
        {"categories": {"bundle"}},
    ),
    # Age / size / condition
    (
        ("κουταβι", "κουταβια", "puppy", "puppies", "koutavi", "junior"),
        {"text_terms": {"puppy", "κουταβ", "junior"}},
    ),
    (
        ("γατακι", "γατακια", "kitten", "kittens", "gataki"),
        {"text_terms": {"kitten", "γατακ"}, "animals": {"cat"}},
    ),
    (
        ("ενηλικα", "ενηλικοσ", "ενηλικη", "adult", "enilika"),
        {"text_terms": {"adult", "ενηλικ"}},
    ),
    (
        ("ηλικιωμενα", "senior", "ageing", "aging", "ilikiomena"),
        {"text_terms": {"senior", "ageing", "ηλικιω"}},
    ),
    (
        (
            "στειρωμενα",
            "στειρωμενη",
            "στειρωμενοσ",
            "στειρωμενη γατα",
            "sterilized",
            "sterilised",
            "sterile",
            "steiromena",
        ),
        {"text_terms": {"steril", "στειρω"}},
    ),
    (
        ("υπερβαρα", "light", "weight control", "weight", "ypervara"),
        {"text_terms": {"light", "weight", "υπερβαρ"}},
    ),
    (
        ("μικροσωμα", "mini", "small breed", "small", "mikrosoma"),
        {"text_terms": {"mini", "small", "μικροσωμ"}},
    ),
    (
        ("μεγαλοσωμα", "maxi", "large breed", "large", "megalosoma"),
        {"text_terms": {"maxi", "large", "μεγαλοσωμ"}},
    ),
    # Health
    (
        ("υποαλλεργικη", "υποαλλεργικο", "hypoallergenic", "hypo", "ypoallergiki"),
        {"text_terms": {"hypo", "υποαλλεργ", "allergen"}},
    ),
    (
        ("urinary", "ουροποιητικο", "ουροποιητικα", "cystitis"),
        {"text_terms": {"urinary", "ουρο"}},
    ),
    (
        ("renal", "νεφρα", "νεφρικ", "kidney"),
        {"text_terms": {"renal", "νεφρ", "kidney"}},
    ),
    (
        (
            "gastrointestinal",
            "γαστρεντερικα",
            "ευαισθητο στομαχι",
            "στομαχι",
            "digestive",
            "gastro",
        ),
        {"text_terms": {"gastro", "digest", "στομαχ", "γαστρ"}},
    ),
    (
        ("τριχοπτωση", "hairball", "derma", "δερμα", "trichoptosi"),
        {"text_terms": {"derma", "hair", "τριχ", "skin"}},
    ),
    (
        (
            "χωρισ σιτηρα",
            "χωρισ δημητριακα",
            "grain free",
            "grainfree",
            "xoris sitira",
        ),
        {"text_terms": {"grain", "σιτηρ", "δημητριακ"}},
    ),
    (
        (
            "μονοπρωτεϊνικη",
            "μονοπρωτεϊνικο",
            "μονοπρωτεϊνη",
            "single protein",
            "monoprotein",
        ),
        {"text_terms": {"single protein", "μονοπρωτε", "single"}},
    ),
    (
        ("holistic", "super premium", "premium", "ολιστικη"),
        {"text_terms": {"premium", "holistic", "ολιστικ"}},
    ),
    # Ingredients
    (
        ("με σολομο", "σολομοσ", "σολομο", "salmon", "solomos"),
        {"text_terms": {"salmon", "σολομ"}},
    ),
    (
        ("με κοτοπουλο", "κοτοπουλο", "chicken", "kotopoulo"),
        {"text_terms": {"chicken", "κοτοπουλ"}},
    ),
    (
        ("με αρνι", "αρνι", "lamb", "arni"),
        {"text_terms": {"lamb", "αρν"}},
    ),
    (
        ("γαλοπουλα", "turkey", "galopoula"),
        {"text_terms": {"turkey", "γαλοπουλ"}},
    ),
    (
        ("βοδινο", "beef", "vodino"),
        {"text_terms": {"beef", "βοδιν"}},
    ),
    (
        ("ψαρι", "fish", "psari"),
        {"text_terms": {"fish", "ψαρ"}},
    ),
    (
        ("ρυζι", "rice", "ryzi"),
        {"text_terms": {"rice", "ρυζ"}},
    ),
    # Hygiene / accessories
    (
        ("σαμπουαν", "shampoo", "sampouan"),
        {"text_terms": {"shampoo", "σαμπ"}},
    ),
    (
        ("λουρι", "leash", "louri"),
        {"text_terms": {"leash", "λουρ"}},
    ),
    (
        ("περιλαιμιο", "κολαρο", "collar", "perilaimio", "kolaro"),
        {"text_terms": {"collar", "περιλαιμ", "κολαρ"}},
    ),
    (
        ("παιχνιδια", "παιχνιδι", "pedia", "paixnidia", "toys", "toy"),
        {"text_terms": {"toy", "παιχνιδ"}},
    ),
    (
        ("λιχουδιεσ", "λιχουδια", "treats", "treat", "lixoudies", "lixoudia"),
        {"text_terms": {"treat", "λιχουδ", "snack"}},
    ),
    (
        ("κοκκαλο", "bone", "kokkalo"),
        {"text_terms": {"bone", "κοκκαλ", "dental"}},
    ),
    (
        (
            "αποπαρασιτωση",
            "τσιμπουρια",
            "ψυλλοι",
            "αμπουλεσ",
            "seresto",
            "bravecto",
            "antiparasitic",
        ),
        {"text_terms": {"paras", "ψυλλ", "τσιμπουρ", "seresto", "bravecto", "αμπουλ"}},
    ),
    # Catalogue brands
    (("ownat", "ουνατ", "own at"), {"companies": {"OWNAT"}}),
    (("profine", "προφαιν", "προφιν", "profain"), {"companies": {"PROFINE"}}),
    (
        ("club4paws", "club 4 paws", "club4 paws", "κλαμπ"),
        {"companies": {"CLUB4PAWS"}},
    ),
    (("everclean", "ever clean", "εβερκλιν"), {"companies": {"EVERCLEAN"}}),
    (("core", "κορ"), {"companies": {"Core"}}),
    (("wild side", "wildside", "γουαιλντ"), {"companies": {"Wild Side"}}),
    (("carnis", "καρνις", "καρνισ"), {"companies": {"Carnis"}}),
    (
        ("puro instinto", "puroinstinto", "πούρο", "instinto"),
        {"companies": {"Puro Instinto"}},
    ),
    # Popular brands users type even if not stocked
    (
        ("royal canin", "ρογιαλ κανιν", "ρογιαλ", "royal"),
        {"text_terms": {"royal", "canin"}},
    ),
    (
        ("purina", "πουρινα", "pro plan", "προ πλαν", "proplan"),
        {"text_terms": {"purina", "pro plan", "proplan"}},
    ),
    (("acana", "ακανα"), {"text_terms": {"acana", "ακανα"}}),
    (("orijen", "οριτζεν"), {"text_terms": {"orijen", "οριτζεν"}}),
    (("whiskas", "ουισκασ"), {"text_terms": {"whiskas"}}),
    (("felix", "φελιξ"), {"text_terms": {"felix"}}),
    (("pedigree", "πεντιγκρι", "πετιγκρι"), {"text_terms": {"pedigree"}}),
    (("monge", "μονζ", "μοντζ"), {"text_terms": {"monge"}}),
    (("farmina", "n&d", "n and d"), {"text_terms": {"farmina", "n&d"}}),
]


def _build_alias_index() -> list[tuple[str, dict]]:
    """Flatten aliases → intent, including auto Greeklish keys, longest first."""
    index: dict[str, dict] = {}
    for aliases, payload in _ALIAS_ROWS:
        for raw in aliases:
            key = normalize_query(raw)
            if len(key) < 2:
                continue
            index[key] = payload
            latin = normalize_query(to_greeklish(key))
            if len(latin) >= 2:
                index.setdefault(latin, payload)
    return sorted(index.items(), key=lambda item: len(item[0]), reverse=True)


_ALIAS_INDEX = _build_alias_index()


def parse_search_query(query: str) -> SearchIntent:
    """
    Resolve a raw user query into structured filters + text groups.
    Longest alias wins; consumed spans are removed so «ξηρά τροφή σκύλου»
    becomes category=dry-food AND animal=dog.
    """
    intent = SearchIntent()
    normalized = normalize_query(query)
    if not normalized:
        return intent

    working = f" {normalized} "
    working_latin = f" {normalize_query(to_greeklish(normalized))} "
    matched_alias = False

    for alias, payload in _ALIAS_INDEX:
        padded = f" {alias} "
        if padded in working:
            _merge_intent(intent, payload)
            working = working.replace(padded, " ")
            latin_alias = normalize_query(to_greeklish(alias))
            working_latin = working_latin.replace(f" {latin_alias} ", " ")
            matched_alias = True
        elif padded in working_latin:
            _merge_intent(intent, payload)
            working_latin = working_latin.replace(padded, " ")
            matched_alias = True

    leftover = normalize_query(working)
    leftover_latin = normalize_query(working_latin)

    leftover_tokens: set[str] = set()
    for token in leftover.split():
        if len(token) >= 2:
            leftover_tokens.add(token)
    for token in leftover_latin.split():
        if len(token) >= 2 and token.isascii():
            leftover_tokens.add(token)

    if leftover_tokens:
        intent.text_groups.append(leftover_tokens)

    # Pure free-text query (no alias hit): match the phrase as typed.
    if not matched_alias and not intent.animals and not intent.categories and not intent.companies:
        group = {normalized}
        original = (query or "").strip()
        if original and len(original) >= 2:
            group.add(original)
        intent.text_groups.append(group)

    return intent


def _product_search_blob(product: Product) -> str:
    """
    Normalized searchable text for one product (Greek-aware).

    Composition/ingredients are intentionally omitted: many recipes list
    chicken meal etc. as a base protein, which would false-match flavour
    searches like «κοτόπουλο».
    """
    parts = [
        product.name or "",
        product.description or "",
        product.bundle_contents or "",
        product.company.name if product.company_id else "",
        product.category.name if product.category_id else "",
        product.category.slug if product.category_id else "",
        product.animal_type.name if product.animal_type_id else "",
        product.animal_type.slug if product.animal_type_id else "",
    ]
    return normalize_query(" ".join(parts))


def _term_hits_blob(term: str, blob: str, blob_latin: str) -> bool:
    needle = normalize_query(term)
    if len(needle) < 2:
        return False
    if needle in blob:
        return True
    latin = normalize_query(to_greeklish(needle))
    return len(latin) >= 2 and latin in blob_latin


def _matches_text_groups(product: Product, groups: list[set[str]]) -> bool:
    blob = _product_search_blob(product)
    blob_latin = normalize_query(to_greeklish(blob))
    for group in groups:
        if not any(_term_hits_blob(term, blob, blob_latin) for term in group):
            return False
    return True


def build_search_queryset(query: str) -> QuerySet[Product]:
    """
    Active products narrowed by structured intent (animal/category/brand).
    Free-text synonym matching is applied in search_products (Python), because
    SQLite cannot case-fold Greek letters reliably.
    """
    intent = parse_search_query(query)
    qs = get_catalog_queryset()

    if intent.animals:
        qs = qs.filter(animal_type__slug__in=intent.animals)
    if intent.categories:
        qs = qs.filter(category__slug__in=intent.categories)
    if intent.companies:
        company_q = Q()
        for name in intent.companies:
            company_q |= Q(company__name__icontains=name)
        qs = qs.filter(company_q)

    # No structured signal and no text groups → nothing to show.
    if (
        not intent.animals
        and not intent.categories
        and not intent.companies
        and not intent.text_groups
    ):
        return qs.none()

    return qs.order_by("-score", "name")


def search_products(query: str, limit: int = SEARCH_SUGGESTION_LIMIT) -> list[Product]:
    cleaned = (query or "").strip()
    if len(cleaned) < 2:
        return []

    intent = parse_search_query(cleaned)
    qs = build_search_queryset(cleaned)

    if not intent.text_groups:
        return list(qs[:limit])

    results: list[Product] = []
    # Catalogue is small; scan favourites-ordered candidates until the limit fills.
    for product in qs.iterator(chunk_size=100):
        if _matches_text_groups(product, intent.text_groups):
            results.append(product)
            if len(results) >= limit:
                break
    return results
