"""
Brand / company landing pages — PDF «Test 1 Site kokkoris (1).pdf».

Built step by step per brand. Each builder returns None if the company has
no dedicated page yet.
"""

PURO_INSTINTO_CODE = "PUR"
CARNIS_CODE = "CAR"
WILD_SIDE_CODE = "WLD"

BRAND_PAGE_CODES = frozenset({PURO_INSTINTO_CODE, CARNIS_CODE, WILD_SIDE_CODE})

# Sampled from PDF page 2.
PURO_BRAND_ACCENT = "#F58220"
PURO_BENEFITS_PILL = "#367C7D"

PURO_BENEFITS_CALLOUTS = (
    {
        "position": "top-left",
        "body": "Με υποαλλεργικές πηγές πρωτεΐνης και χωρίς γλουτένη…",
    },
    {
        "position": "top-right",
        "body": "Βελτιώνει την αναλογία λιπαρών οξέων Ω3 και Ω6…",
    },
    {
        "position": "upper-mid-left",
        "body": "Με χονδροϊτίνη, βιοτίνη και ωμέγα-3…",
    },
    {
        "position": "upper-mid-right",
        "body": "Με DHA, EPA και Ταυρίνη…",
    },
    {
        "position": "mid-left",
        "body": "Τα πρεβιοτικά FOS και MOS…",
    },
    {
        "position": "mid-right",
        "body": "Χονδροϊτίνη και γλυκοζαμίνη…",
    },
    {
        "position": "lower-left",
        "body": "Η L-Καρνιτίνη βοηθά στη μετατροπή του λίπους σε ενέργεια.",
    },
    {
        "position": "lower-right",
        "body": "Εκχύλισμα yucca για να μειωθούν οι άσχημες οσμές…",
    },
    {
        "position": "bottom-center",
        "body": "Η λυσίνη προάγει την ανάπτυξη των οστών.",
    },
)

PURO_STORY_BLOCKS = (
    {
        "title": "Πάντα με κύριο συστατικό",
        "title_suffix": "το κρέας",
        "body": (
            "Απλές συνταγές, με λίγα υλικά για αποφυγή τροφικών δυσανεξιών και με "
            "βασικό συστατικό πάντα το κρέας και το ψάρι, παρέχοντας ιδιαίτερα "
            "εύπεπτες πρωτεΐνες. Επιπλέον, τα φυσικά αντιοξειδωτικά, τα ωμέγα 3&6, "
            "οι ζυμομύκητες, οι βιταμίνες και τα χηλικά μέταλλα που περιέχουν "
            "συμβάλλουν στη διατήρηση ενός υγιούς ανοσοποιητικού συστήματος, "
            "παρέχοντας καλύτερη υγεία στο κατοικίδιο ζώο σας και παρατείνοντας "
            "τη ζωή του. Ιδανικό για ζώα με ή χωρίς τροφικές ευαισθησίες."
        ),
        "image_static": "images/brand-page/puro-instinto/story-bowl.png",
        "image_side": "right",
    },
    {
        "title": "Κατάλληλο για όλα τα ζώα:",
        "title_suffix": "",
        "body": (
            "Οι φόρμουλές μας με χαμηλά δημητριακά μειώνουν την πιθανότητα τα "
            "ζώα να αναπτύξουν τροφικές ευαισθησίες επειδή παρασκευάζονται με "
            "λίγα μόνο συστατικά. Ο μικρότερος αριθμός συστατικών μας επιτρέπει "
            "να παρασκευάζουμε απλές και ολοκληρωμένες συνταγές που αποτρέπουν "
            "την εμφάνιση αλλεργικών αντιδράσεων σε ορισμένα τρόφιμα."
        ),
        "image_static": "images/brand-page/puro-instinto/story-pets.png",
        "image_side": "left",
    },
    {
        "title": "Επίδραση γιαουρτιού:",
        "title_suffix": "",
        "body": (
            "Οι μαννάν-ολιγοσακχαρίτες (MOS) και οι φρουκτο-ολιγοσακχαρίτες (FOS) "
            "που ενσωματώνονται στις φόρμουλές μας Puro Instinto είναι ζωντανές "
            "προβιοτικές καλλιέργειες, όπως αυτές που υπάρχουν στο γιαούρτι, και "
            "βοηθούν στην καλή πέψη."
        ),
        "image_static": "",
        "image_side": "none",
        "full_width": True,
    },
)

# Carnis — PDF page 3, teal accent from dog-food section.
CARNIS_BRAND_ACCENT = "#28C4B0"

# Wild Side — PDF page 4, orange hero / teal cat detail.
WILD_SIDE_BRAND_ACCENT = "#FF931E"


def _build_puro_context(company):
    return {
        "company": company,
        "page_title": "Puro Instinto",
        "hero_band_static": "images/brand-page/puro-instinto/benefits-hero-clean.png",
        "story_band_static": "images/brand-page/puro-instinto/story-section-clean.png",
        "product_detail_static": "images/brand-page/puro-instinto/product-detail-clean.png",
        "story_blocks": PURO_STORY_BLOCKS,
        "brand_accent": PURO_BRAND_ACCENT,
        "show_products_row": True,
        "show_product_detail": True,
    }


def _build_carnis_context(company):
    """PDF page 3 — hero, teal dog story, dog products, white cat story, cat products."""
    return {
        "company": company,
        "page_title": "Carnis",
        "hero_band_static": "images/brand-page/carnis/benefits-hero-clean.png",
        "page_sections": (
            {
                "type": "story",
                "static": "images/brand-page/carnis/story-teal-dog.png",
                "section_class": "brand-story-band--teal",
            },
            {
                "type": "products",
                "animal_type": "Dog",
                "category": "Dry Food",
                "products_row_class": "brand-products--teal",
            },
            {
                "type": "story",
                "static": "images/brand-page/carnis/story-white-cat.png",
                "section_class": "brand-story-band--white",
            },
            {
                "type": "products",
                "animal_type": "Cat",
                "category": "Dry Food",
                "products_row_class": "brand-products--teal",
            },
        ),
        "brand_accent": CARNIS_BRAND_ACCENT,
        "show_product_detail": False,
    }


def _build_wild_side_context(company):
    """PDF page 4 — orange hero, dog story, products, cat story, products."""
    return {
        "company": company,
        "page_title": "Wild Side",
        "hero_band_static": "images/brand-page/wild-side/benefits-hero-clean.png",
        "hero_section_class": "brand-hero-orange",
        "page_sections": (
            {
                "type": "story",
                "static": "images/brand-page/wild-side/story-white-dog.png",
                "section_class": "brand-story-band--white",
            },
            {
                "type": "products",
                "products_row_class": "brand-products--orange brand-products--wild-gap-before-cat",
            },
            {
                "type": "story",
                "static": "images/brand-page/wild-side/story-white-cat.png",
                "section_class": "brand-story-band--white brand-story-band--wild-cat-intro",
            },
            {
                "type": "story",
                "static": "images/brand-page/wild-side/story-teal-cat.png",
                "section_class": "brand-story-band--teal",
            },
            {
                "type": "products",
                "products_row_class": "brand-products--teal",
            },
        ),
        "brand_accent": WILD_SIDE_BRAND_ACCENT,
        "show_product_detail": False,
    }


_BUILDERS = {
    PURO_INSTINTO_CODE: _build_puro_context,
    CARNIS_CODE: _build_carnis_context,
    WILD_SIDE_CODE: _build_wild_side_context,
}


def has_brand_page(company_code):
    return company_code.upper() in BRAND_PAGE_CODES


def build_company_page_context(company):
    """Context for a dedicated brand page, or None if not implemented yet."""
    builder = _BUILDERS.get(company.code.upper())
    if builder is None:
        return None
    return builder(company)
