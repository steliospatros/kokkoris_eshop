"""
Generate professional Greek storefront descriptions for pet-food products.

Uses product metadata (brand, animal, category, name, short seed text) to
produce engaging, consistent copy without inventing unsupported nutrition claims.
"""
from __future__ import annotations

import re

FLAVOR_PATTERNS = [
    (r"chicken|κοτ[οό]πουλ", "κοτόπουλο", "κοτόπουλου"),
    (r"turkey|γαλοπο[υύ]λ", "γαλοπούλα", "γαλοπούλας"),
    (r"lamb|αρν[ιί]", "αρνί", "αρνιού"),
    (r"beef|βοδιν|μοσχ[αά]ρ", "μοσχάρι", "μοσχαριού"),
    (r"salmon|σολομ", "σολομό", "σολομού"),
    (r"fish|ψ[αά]ρ", "ψάρι", "ψαριού"),
    (r"duck|π[αά]πι", "πάπια", "πάπιας"),
    (r"rabbit|κουν[εέ]λ", "κουνέλι", "κουνελιού"),
    (r"mackerel|σκουμπρ", "σκουμπρί", "σκουμπριού"),
    (r"venison|ελαφ", "ελάφι", "ελαφιού"),
]

STAGE_PATTERNS = [
    (r"kitten|γατακ", "kitten"),
    (r"puppy|puppies|κουταβ|junior", "puppy"),
    (r"senior|ageing|aging|ηλικιωμ|mature", "senior"),
    (r"steriliz|στειρωμ", "sterilized"),
    (r"light|weight|β[αά]ρουσ|ελεγχο βαρ", "light"),
    (r"energy|δραστηρ", "energy"),
    (r"hairball|τριχομπ", "hairball"),
    (r"sensitive|ευαισθητ|derma|δ[εέ]ρμα", "sensitive"),
    (r"adult|ενηλικ", "adult"),
]

BREED_PATTERNS = [
    (r"small|mini|μικρ[οό]σωμ", "small"),
    (r"large|maxi|μεγαλ[οό]σωμ", "large"),
    (r"medium|μεσα[ιί]ων", "medium"),
]


def _match_first(text: str, patterns):
    for pattern, *values in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return values[0] if len(values) == 1 else tuple(values)
    return None


def _animal_forms(animal: str) -> dict:
    if animal == "Cat":
        return {
            "pl_acc": "γάτες",
            "adult_acc": "ενήλικες γάτες",
            "sterilized_acc": "στειρωμένες γάτες",
            "active_acc": "δραστήριες γάτες",
            "senior_acc": "μεγαλύτερες γάτες",
            "possessive": "της γάτας σας",
        }
    return {
        "pl_acc": "σκύλους",
        "adult_acc": "ενήλικους σκύλους",
        "sterilized_acc": "στειρωμένους σκύλους",
        "active_acc": "δραστήριους σκύλους",
        "senior_acc": "μεγαλύτερους σκύλους",
        "possessive": "του σκύλου σας",
    }


def _flavor_phrase(flavor_genitive: str | None) -> str:
    if not flavor_genitive:
        return "εκλεκτά συστατικά υψηλής ποιότητας"
    return f"πλούσια γεύση {flavor_genitive}"


def _stage_opening(stage: str | None, forms: dict, breed: str | None) -> str:
    breed_bit = {
        "small": " μικρόσωμων φυλών",
        "large": " μεγαλόσωμων φυλών",
        "medium": " μεσαίων φυλών",
    }.get(breed or "", "")

    mapping = {
        "kitten": f"ιδανική επιλογή για γατάκια{breed_bit} στην κρίσιμη φάση ανάπτυξης",
        "puppy": (
            f"ιδανική επιλογή για κουτάβια{breed_bit} με ανάγκες υψηλής ενέργειας "
            f"και σωστής ανάπτυξης"
        ),
        "senior": (
            f"ιδανική επιλογή για {forms['senior_acc']}{breed_bit}, "
            f"με ήπια και ισορροπημένη σύνθεση"
        ),
        "sterilized": (
            f"κατάλληλη επιλογή για {forms['sterilized_acc']}{breed_bit}, "
            f"με ισορροπημένο προφίλ για καθημερινή φροντίδα"
        ),
        "light": (
            f"ιδανική επιλογή για έλεγχο βάρους σε {forms['pl_acc']}{breed_bit}, "
            f"χωρίς να θυσιάζει τη γεύση"
        ),
        "energy": (
            f"ενεργειακή φόρμουλα για {forms['active_acc']}{breed_bit} "
            f"με υψηλές απαιτήσεις"
        ),
        "hairball": (
            "ιδανική επιλογή για καθημερινό έλεγχο των τριχόμπαλων, "
            "με σύνθεση φιλική για ευαίσθητο πεπτικό"
        ),
        "sensitive": (
            f"ήπια σύνθεση για {forms['pl_acc']} με ευαίσθητο πεπτικό "
            f"ή ανάγκες φροντίδας δέρματος και τριχώματος"
        ),
        # Accusative after «αποτελεί»: πλήρη (not πλήρης)
        "adult": f"πλήρη καθημερινή διατροφή για {forms['adult_acc']}{breed_bit}",
    }
    if stage in mapping:
        return mapping[stage]
    return f"πλήρη καθημερινή διατροφή για {forms['pl_acc']}{breed_bit}"


def _category_body(category: str, flavor_acc: str | None, flavor_gen: str | None, possessive: str) -> str:
    flavor_txt = _flavor_phrase(flavor_gen)
    if category == "Dry Food":
        return (
            f"Η ξηρά τροφή προσφέρει {flavor_txt} και σταθερή θρέψη για την καθημερινότητα "
            f"{possessive}, υποστηρίζοντας ζωτικότητα, ευεξία και λαμπερό τρίχωμα."
        )
    if category == "Sachets":
        sauce = "σε ζελέ ή σάλτσα" if not flavor_acc else f"με {flavor_acc}"
        return (
            f"Το φακελάκι {sauce} είναι πρακτική, απολαυστική επιλογή γεύματος που "
            f"ενυδατώνει και δελεάζει ακόμη και τους πιο απαιτητικούς ουρανίσκους."
        )
    if category == "Canned Food":
        return (
            f"Η κονσέρβα με {flavor_txt} προσφέρει υγρή, πλούσια σε κρέας υφή και "
            f"έντονο άρωμα για γεύματα που ξεχωρίζουν."
        )
    if category == "Bundle":
        return (
            "Το ποικιλιακό πακέτο συνδυάζει διαφορετικές γεύσεις σε μία συσκευασία, "
            "ιδανικό για εναλλαγή και καθημερινή απόλαυση χωρίς συμβιβασμούς στην ποιότητα."
        )
    if category == "Litter":
        return (
            "Αξιόπιστη επιλογή άμμου με αποτελεσματικό έλεγχο οσμών και άνεση για την "
            "καθημερινή υγιεινή στο σπίτι."
        )
    return (
        f"Προσεκτικά επιλεγμένη σύνθεση με {flavor_txt}, για διατροφή που κερδίζει "
        f"εμπιστοσύνη σε κάθε γεύμα."
    )


def _brand_close(company: str) -> str:
    closes = {
        "OWNAT": (
            "Η ποιότητα Ownat στηρίζεται σε φυσικά συστατικά και συνταγές που "
            "σέβονται τις πραγματικές ανάγκες του κατοικίδιου σας."
        ),
        "PROFINE": (
            "Η σειρά Profine Superpremium συνδυάζει υψηλή πεπτικότητα με γεύση "
            "που αγαπούν τα κατοικίδια."
        ),
        "CLUB4PAWS": (
            "Με κρέας υψηλής ποιότητας και ισορροπημένη σύνθεση, η Club4Paws "
            "κάνει κάθε γεύμα στιγμή φροντίδας."
        ),
        "EVERCLEAN": (
            "Η Ever Clean προσφέρει καθαριότητα και αξιοπιστία για άνετη "
            "καθημερινότητα στο σπίτι."
        ),
        "Core": (
            "Η Core εστιάζει σε καθαρές, υψηλής διατροφικής αξίας συνθέσεις "
            "για απαιτητικούς κηδεμόνες."
        ),
        "Wild Side": "Η Wild Side φέρνει έντονη γεύση και χαρακτήρα σε κάθε γεύμα.",
        "Puro Instinto": (
            "Η Puro Instinto ακολουθεί μια πιο φυσική προσέγγιση στη διατροφή "
            "του κατοικίδιου σας."
        ),
    }
    return closes.get(
        company,
        "Επιλέξτε ποιότητα που φαίνεται στην όρεξη, την ενέργεια και τη συνολική "
        "ευεξία του κατοικίδιου σας.",
    )


def _is_catalogue_tagline(seed: str) -> bool:
    """Skip raw ALL-CAPS catalogue lines like 'ΜΕ ΚΟΤΟΠΟΥΛΟ - ΓΙΑ ΕΝΗΛΙΚΟΥΣ ΣΚΥΛΟΥΣ'."""
    letters = [c for c in seed if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    if upper_ratio >= 0.55 and len(seed) < 100:
        return True
    if re.match(r"^Μ[ΕE]\s+.+\s*[—\-]\s*ΓΙΑ\s+", seed, re.IGNORECASE):
        return True
    return False


def _clean_seed(seed: str) -> str:
    seed = (seed or "").strip()
    if not seed:
        return ""
    if seed.lower().startswith("περιέχει:"):
        return seed if seed.endswith(".") else seed + "."
    if _is_catalogue_tagline(seed):
        return ""
    # Already AI-enriched / long marketing text — don't re-embed as seed.
    if len(seed) > 100:
        return ""
    seed = re.sub(r"^ΜΕ\s+", "Με ", seed, flags=re.IGNORECASE)
    seed = re.sub(r"\s*-\s*", " — ", seed)
    if not seed.endswith("."):
        seed = seed.rstrip(" .") + "."
    return seed


def generate_product_description(
    *,
    name: str,
    company: str,
    animal: str,
    category: str,
    seed_description: str = "",
    bundle_contents: str = "",
) -> str:
    forms = _animal_forms(animal)
    haystack = f"{name} {seed_description} {bundle_contents}"
    flavor_match = _match_first(haystack, FLAVOR_PATTERNS)
    if flavor_match:
        flavor_acc, flavor_gen = flavor_match
    else:
        flavor_acc, flavor_gen = None, None
    stage = _match_first(haystack, STAGE_PATTERNS) or "adult"
    breed = _match_first(haystack, BREED_PATTERNS)

    opening = _stage_opening(stage, forms, breed)
    body = _category_body(category, flavor_acc, flavor_gen, forms["possessive"])
    brand = _brand_close(company)
    seed = _clean_seed(seed_description)

    parts = [
        f"Το {company} «{name}» αποτελεί {opening}.",
        body,
    ]

    if seed and seed.lower() not in body.lower() and not seed.lower().startswith("περιέχει:"):
        if len(seed) <= 100:
            parts.insert(1, seed)

    if category == "Bundle" and bundle_contents:
        parts.insert(1, f"Περιεχόμενο ποικιλίας: {bundle_contents.strip()}.")
    elif seed.lower().startswith("περιέχει:"):
        parts.insert(1, seed)

    parts.append(brand)
    text = " ".join(p.strip() for p in parts if p and p.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 520:
        text = text[:517].rsplit(" ", 1)[0].rstrip(",;") + "."
    return text
