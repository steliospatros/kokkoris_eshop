"""
Box Now locker shipping cost and compartment-size selection.

Compartment sizes follow the Box Now Partner API:
  1 = Small, 2 = Medium, 3 = Large
"""
import math
from decimal import Decimal

from django.conf import settings

from products.utils import VOLUMETRIC_DIVISOR, _resolve_product

COMPARTMENT_SMALL = 1
COMPARTMENT_MEDIUM = 2
COMPARTMENT_LARGE = 3

COMPARTMENT_LABELS = {
    COMPARTMENT_SMALL: "Μικρό",
    COMPARTMENT_MEDIUM: "Μεσαίο",
    COMPARTMENT_LARGE: "Μεγάλο",
}


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


def determine_compartment_size(cart_items):
    """
    Map cart contents to a Box Now locker compartment size.

    Thresholds are configurable via BOXNOW_SMALL_MAX_KG / BOXNOW_MEDIUM_MAX_KG.
    """
    weight_kg = calculate_cart_chargeable_weight_kg(cart_items)
    small_max = Decimal(str(settings.BOXNOW_SMALL_MAX_KG))
    medium_max = Decimal(str(settings.BOXNOW_MEDIUM_MAX_KG))

    if weight_kg <= small_max:
        return COMPARTMENT_SMALL
    if weight_kg <= medium_max:
        return COMPARTMENT_MEDIUM
    return COMPARTMENT_LARGE


def exceeds_boxnow_weight_limit(cart_items):
    """True when the cart is too heavy for any BOX NOW locker."""
    weight_kg = calculate_cart_chargeable_weight_kg(cart_items)
    max_kg = Decimal(str(settings.BOXNOW_MAX_WEIGHT_KG))
    return weight_kg > max_kg


def calculate_boxnow_shipping_cost(cart_items, cart_total, region):
    """
    Box Now shipping fee based on locker compartment size.

    Free shipping applies for orders of €70+ (same rule as courier).
    """
    cart_total = Decimal(cart_total)

    if cart_total >= Decimal(str(settings.FREE_SHIPPING_ORDER_MINIMUM)):
        return Decimal("0.00")

    compartment = determine_compartment_size(cart_items)
    fee_map = {
        COMPARTMENT_SMALL: settings.BOXNOW_FEE_SMALL,
        COMPARTMENT_MEDIUM: settings.BOXNOW_FEE_MEDIUM,
        COMPARTMENT_LARGE: settings.BOXNOW_FEE_LARGE,
    }
    return Decimal(fee_map[compartment]).quantize(Decimal("0.01"))


def cart_weight_grams(cart_items):
    """Parcel weight for the Box Now API (grams, rounded up)."""
    weight_kg = calculate_cart_chargeable_weight_kg(cart_items)
    return max(1, math.ceil(float(weight_kg * Decimal("1000"))))
