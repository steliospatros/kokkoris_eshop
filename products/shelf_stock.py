"""
Warehouse shelf count from the handwritten stock list.

Everything else stays on-order with shop quantity 0: those bags belong to
supplier stock, not the storefront warehouse.
"""
from decimal import Decimal

from products.models import Product, ProductVariant

# Carnis cat bags in the catalog were 2 kg / 4 kg; the warehouse list uses
# 3 kg / 7 kg. Kitten packs stay 2 kg / 4 kg.
CARNIS_CAT_WEIGHT_UPDATES = (
    ("Σολομός ξηρά τροφή - για ενήλικες γάτες", Decimal("2.00"), Decimal("3.00")),
    ("Σολομός ξηρά τροφή - για ενήλικες γάτες", Decimal("4.00"), Decimal("7.00")),
    ("Classic ξηρά τροφή - για ενήλικες γάτες", Decimal("2.00"), Decimal("3.00")),
    ("Classic ξηρά τροφή - για ενήλικες γάτες", Decimal("4.00"), Decimal("7.00")),
    ("Adult XL γαλοπούλα ξηρά τροφή - για μεγαλόσωμες γάτες", Decimal("2.00"), Decimal("3.00")),
    ("Adult XL γαλοπούλα ξηρά τροφή - για μεγαλόσωμες γάτες", Decimal("4.00"), Decimal("7.00")),
)

# (company name, product name, weight kg, quantity, optional note)
SHELF_ITEMS = (
    (
        "Puro Instinto",
        "4 Meats ξηρά τροφή - για ενήλικους σκύλους",
        Decimal("15.00"),
        103,
        "Χειρόγραφο: Puro 10kg (CATA) → 103. Στο κατάλογο το σακί είναι 15 kg.",
    ),
    (
        "Puro Instinto",
        "Chicken ξηρά τροφή - για ενήλικες γάτες",
        Decimal("3.00"),
        29,
        "",
    ),
    (
        "Wild Side",
        "Deep Forest ξηρά τροφή - για ενήλικους σκύλους",
        Decimal("10.40"),
        88,
        "",
    ),
    (
        "Wild Side",
        "African Sunset ξηρά τροφή - για ενήλικους σκύλους",
        Decimal("10.40"),
        24,
        "",
    ),
    (
        "OWNAT",
        "Ξηρά τροφή Classic Complet - για ενήλικους σκύλους",
        Decimal("12.00"),
        7,
        "",
    ),
    (
        "OWNAT",
        "Ξηρά τροφή Ultra Medium - για ενήλικους σκύλους",
        Decimal("12.00"),
        1,
        "Χειρόγραφο: Ownat Dog Campatrice → 1 σακί 12 kg. Αντιστοιχίστηκε στο Ultra Medium (χωρίς δημητριακά).",
    ),
    (
        "OWNAT",
        "Ξηρά τροφή Ultra - για νεαρές γάτες",
        Decimal("3.00"),
        2,
        "Ownat Cat Grain Free 3 kg.",
    ),
    (
        "OWNAT",
        "Κοτόπουλο ξηρά τροφή Classic - για ενήλικες γάτες",
        Decimal("4.00"),
        1,
        "",
    ),
    (
        "OWNAT",
        "Κοτόπουλο ξηρά τροφή Classic Light - για ενήλικες γάτες",
        Decimal("4.00"),
        2,
        "",
    ),
    (
        "CLUB4PAWS",
        "Κοτόπουλο ξηρά τροφή - για ενήλικους σκύλους μεσαίων ρατσών",
        Decimal("14.00"),
        2,
        "",
    ),
    (
        "CLUB4PAWS",
        "Κοτόπουλο ξηρά τροφή - για ενήλικους σκύλους μεγαλόσωμων ρατσών",
        Decimal("14.00"),
        2,
        "",
    ),
    (
        "CLUB4PAWS",
        "Γαλοπούλα ξηρά τροφή - για στειρωμένες γάτες",
        Decimal("14.00"),
        1,
        "",
    ),
    (
        "CLUB4PAWS",
        "Κοτόπουλο ξηρά τροφή - για γάτες με τριχόμπαλες",
        Decimal("14.00"),
        1,
        "",
    ),
    (
        "CLUB4PAWS",
        "Κοτόπουλο ξηρά τροφή - για γάτες με ευαίσθητο ουροποιητικό",
        Decimal("14.00"),
        2,
        "",
    ),
    (
        "Carnis",
        "Σολομός ξηρά τροφή - για ενήλικες γάτες",
        Decimal("7.00"),
        9,
        "",
    ),
    (
        "Carnis",
        "Classic ξηρά τροφή - για ενήλικες γάτες",
        Decimal("7.00"),
        12,
        "",
    ),
    (
        "Carnis",
        "Σολομός ξηρά τροφή - για ενήλικες γάτες",
        Decimal("3.00"),
        18,
        "",
    ),
    (
        "Carnis",
        "Classic ξηρά τροφή - για ενήλικες γάτες",
        Decimal("3.00"),
        11,
        "",
    ),
    (
        "Carnis",
        "Adult XL γαλοπούλα ξηρά τροφή - για μεγαλόσωμες γάτες",
        Decimal("3.00"),
        9,
        "",
    ),
)


def update_carnis_cat_weights():
    """Rename Carnis adult-cat pack sizes from 2/4 kg to 3/7 kg."""
    changed = []
    for name, old_weight, new_weight in CARNIS_CAT_WEIGHT_UPDATES:
        variant = ProductVariant.objects.filter(
            product__company__name="Carnis",
            product__name=name,
            weight=old_weight,
        ).first()
        if variant is None:
            continue
        variant.weight = new_weight
        variant.save(update_fields=["weight"])
        changed.append((name, old_weight, new_weight, variant.pk))
    return changed


def find_shelf_variant(company_name, product_name, weight):
    variant = ProductVariant.objects.select_related(
        "product", "product__company"
    ).filter(
        product__company__name=company_name,
        product__name=product_name,
        weight=weight,
    ).first()
    if variant:
        return variant
    for name, old_weight, new_weight in CARNIS_CAT_WEIGHT_UPDATES:
        if (
            company_name == "Carnis"
            and product_name == name
            and weight == new_weight
        ):
            return ProductVariant.objects.select_related(
                "product", "product__company"
            ).filter(
                product__company__name="Carnis",
                product__name=name,
                weight=old_weight,
            ).first()
    return None


def apply_warehouse_stock(*, dry_run=False):
    """
    Put every variant on-order with shop stock 0, then apply the shelf list.

    Returns a dict with counts, warnings, and missing lookups.
    """
    report = {
        "weight_updates": [],
        "on_order": 0,
        "shelf": [],
        "warnings": [],
        "missing": [],
    }

    if not dry_run:
        report["weight_updates"] = update_carnis_cat_weights()
    else:
        for name, old_weight, new_weight in CARNIS_CAT_WEIGHT_UPDATES:
            exists = ProductVariant.objects.filter(
                product__company__name="Carnis",
                product__name=name,
                weight=old_weight,
            ).exists()
            if exists:
                report["weight_updates"].append((name, old_weight, new_weight, None))

    lookups = []
    for company_name, product_name, weight, quantity, note in SHELF_ITEMS:
        variant = find_shelf_variant(company_name, product_name, weight)
        if variant is None:
            report["missing"].append(
                f"{company_name} · {product_name} · {weight} kg"
            )
            continue
        lookups.append((variant, quantity, note))
        if note:
            report["warnings"].append(note)

    if report["missing"]:
        return report

    if dry_run:
        report["on_order"] = ProductVariant.objects.count()
        report["shelf"] = [
            (variant.pk, variant.product.name, variant.weight, quantity)
            for variant, quantity, _note in lookups
        ]
        return report

    report["on_order"] = ProductVariant.objects.update(
        stock=0,
        availability=ProductVariant.AVAILABILITY_ON_ORDER,
    )
    for variant, quantity, _note in lookups:
        variant.refresh_from_db()
        variant.stock = quantity
        variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
        variant.save(update_fields=["stock", "availability"])
        report["shelf"].append(
            (variant.pk, variant.product.name, variant.weight, quantity)
        )
    return report
