"""
Box Now locker shipping: compartment size, weight/dimension limits, fee.

Locker inner sizes and the 20 kg cap come from BOX NOW locker info
(compartmentSize 1/2/3 in Partner API v1.68). Partner fees are the shop's
contract rates in settings (BOXNOW_FEE_*).
"""
from decimal import Decimal

from django.conf import settings

from products.catalog import format_decimal_greek
from products.utils import VOLUMETRIC_DIVISOR, _resolve_product

COMPARTMENT_SMALL = 1
COMPARTMENT_MEDIUM = 2
COMPARTMENT_LARGE = 3

COMPARTMENT_LABELS = {
    COMPARTMENT_SMALL: "Μικρή",
    COMPARTMENT_MEDIUM: "Μεσαία",
    COMPARTMENT_LARGE: "Μεγάλη",
}

# Official locker inner sizes (H × W × L cm) — BOX NOW locker-info.
COMPARTMENT_INNER_CM = {
    COMPARTMENT_SMALL: (8, 45, 60),
    COMPARTMENT_MEDIUM: (17, 45, 60),
    COMPARTMENT_LARGE: (36, 45, 60),
}

COMPARTMENT_DIM_LABELS = {
    COMPARTMENT_SMALL: "8×45×60 cm",
    COMPARTMENT_MEDIUM: "17×45×60 cm",
    COMPARTMENT_LARGE: "36×45×60 cm",
}


def max_locker_weight_kg():
    return Decimal(str(settings.BOXNOW_MAX_WEIGHT_KG))


def calculate_cart_chargeable_weight_kg(cart_items):
    """Billable weight (kg): max of real vs volumetric weight."""
    total_real_weight = Decimal("0.00")
    total_volumetric_weight = Decimal("0.00")

    for item in cart_items:
        product = _resolve_product(item)
        quantity = Decimal(getattr(item, "quantity", 1))
        total_real_weight += Decimal(product.weight) * quantity
        item_volumetric_weight = (
            Decimal(product.length)
            * Decimal(product.width)
            * Decimal(product.height)
        ) / VOLUMETRIC_DIVISOR
        total_volumetric_weight += item_volumetric_weight * quantity

    return max(total_real_weight, total_volumetric_weight)


def _item_dims_cm(item):
    product = _resolve_product(item)
    return (
        float(product.length or 0),
        float(product.width or 0),
        float(product.height or 0),
    )


def _fits_compartment(dims, compartment):
    inner = COMPARTMENT_INNER_CM[compartment]
    package = sorted(dims, reverse=True)
    box = sorted(inner, reverse=True)
    return all(package[i] <= box[i] + 0.05 for i in range(3))


def _item_required_compartment(item):
    """Smallest locker that can hold one unit of this line, or None if none."""
    dims = _item_dims_cm(item)
    if all(d <= 0 for d in dims):
        weight = Decimal(_resolve_product(item).weight)
        if weight <= Decimal("2"):
            return COMPARTMENT_SMALL
        if weight <= Decimal("7"):
            return COMPARTMENT_MEDIUM
        if weight <= max_locker_weight_kg():
            return COMPARTMENT_LARGE
        return None
    for size in (COMPARTMENT_SMALL, COMPARTMENT_MEDIUM, COMPARTMENT_LARGE):
        if _fits_compartment(dims, size):
            return size
    return None


def determine_compartment_size(cart_items):
    """
    Smallest Box Now compartment that can take the whole cart as one parcel.

    Multi-item orders use the largest size required by any single unit.
    Combined volume must still fit the large locker.
    """
    if not cart_items:
        return COMPARTMENT_SMALL

    required = COMPARTMENT_SMALL
    total_volume = 0.0
    for item in cart_items:
        quantity = int(getattr(item, "quantity", 1) or 1)
        size = _item_required_compartment(item)
        if size is None:
            return None
        required = max(required, size)
        l, w, h = _item_dims_cm(item)
        if l > 0 and w > 0 and h > 0:
            total_volume += l * w * h * quantity

    large = COMPARTMENT_INNER_CM[COMPARTMENT_LARGE]
    large_volume = large[0] * large[1] * large[2]
    if total_volume > large_volume + 1:
        return None
    return required


def exceeds_boxnow_weight_limit(cart_items):
    """True when weight or dimensions will not fit any BOX NOW locker."""
    if calculate_cart_chargeable_weight_kg(cart_items) > max_locker_weight_kg():
        return True
    return determine_compartment_size(cart_items) is None


def calculate_boxnow_shipping_cost(cart_items, cart_total, region):
    """Box Now fee from the selected compartment, or 0 above free-shipping."""
    cart_total = Decimal(cart_total)

    if cart_total >= Decimal(str(settings.FREE_SHIPPING_ORDER_MINIMUM)):
        return Decimal("0.00")

    compartment = determine_compartment_size(cart_items)
    if compartment is None:
        return Decimal("0.00")

    fee_map = {
        COMPARTMENT_SMALL: settings.BOXNOW_FEE_SMALL,
        COMPARTMENT_MEDIUM: settings.BOXNOW_FEE_MEDIUM,
        COMPARTMENT_LARGE: settings.BOXNOW_FEE_LARGE,
    }
    return Decimal(fee_map[compartment]).quantize(Decimal("0.01"))


def cart_weight_kg(cart_items):
    """Parcel weight for Partner API v1.68 (kg, up to 3 decimal places)."""
    weight = calculate_cart_chargeable_weight_kg(cart_items)
    return float(weight.quantize(Decimal("0.001")))


def cart_weight_grams(cart_items):
    """Deprecated alias — API 1.68 expects kilograms, not grams."""
    return cart_weight_kg(cart_items)


def build_boxnow_option_copy(cart_items, *, too_heavy, fee, free_minimum):
    """Customer-facing description and unavailable message for checkout."""
    weight = calculate_cart_chargeable_weight_kg(cart_items)
    weight_label = format_decimal_greek(weight)
    max_label = format_decimal_greek(max_locker_weight_kg())
    compartment = determine_compartment_size(cart_items)

    if too_heavy:
        return (
            "Μη διαθέσιμο — το δέμα δεν χωρά σε locker BOX NOW.",
            (
                f"Το BOX NOW δέχεται έως {max_label} kg και μέγιστες διαστάσεις "
                f"μεγάλης θήκης {COMPARTMENT_DIM_LABELS[COMPARTMENT_LARGE]}. "
                f"Το καλάθι σας ζυγίζει {weight_label} kg (χρεώσιμο βάρος). "
                "Επιλέξτε αποστολή με courier."
            ),
        )

    dim_label = COMPARTMENT_DIM_LABELS.get(compartment, "")
    size_label = COMPARTMENT_LABELS.get(compartment, "")
    if fee:
        price_bit = f"Χρέωση {format_decimal_greek(fee)} €."
    else:
        price_bit = (
            f"Δωρεάν μεταφορικά — η παραγγελία σας ξεπερνά τα "
            f"{format_decimal_greek(free_minimum)} €."
        )
    description = (
        f"Παράλαβε από αυτόματο locker BOX NOW. "
        f"Θήκη {size_label} ({dim_label}) · βάρος {weight_label} kg "
        f"(όριο {max_label} kg). {price_bit} "
        "Επίλεξε σημείο παραλαβής στον χάρτη."
    )
    return description, ""
