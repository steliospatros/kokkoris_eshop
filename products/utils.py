"""
Product catalogue utilities, including volumetric-weight helpers.

The former weight-based (ELTA-style) courier tariff in calculate_shipping_cost
is no longer used at checkout; door courier is a flat fee in
checkout.delivery.calculate_courier_fee. These helpers remain for BOX NOW
locker sizing and the cash-on-delivery surcharge.
"""
import math
from decimal import Decimal

from django.conf import settings

# Region label used by the free-shipping rule below. Attica postal codes in
# Greece typically start with 10–19; anything else is treated as non-Attica.
REGION_ATTICA = "Attica"

# Former ELTA Courier tariff constants. Checkout no longer uses the
# weight-based table; COD_FEE and VOLUMETRIC_DIVISOR are still used
# (payment surcharge and BOX NOW locker sizing).
BASE_FEE = Decimal("2.00")
BASE_WEIGHT_LIMIT = Decimal("2.0")
EXTRA_KG_FEE = Decimal("0.80")
COD_FEE = Decimal("1.50")
VOLUMETRIC_DIVISOR = Decimal("5000")

# Legacy aliases — prefer settings.FREE_SHIPPING_ORDER_MINIMUM in new code.
FREE_SHIPPING_ORDER_MINIMUM = Decimal("60.00")
FREE_SHIPPING_ATTICA_MINIMUM = FREE_SHIPPING_ORDER_MINIMUM
FREE_SHIPPING_CART_MINIMUM = FREE_SHIPPING_ORDER_MINIMUM


def postal_code_to_region(postal_code):
    """
    Map a Greek postal code (T.K.) to a coarse region label for shipping rules.

    Attica prefecture codes generally begin with 10–19. This is a deliberate
    approximation for tariff purposes, not an exact municipal boundary lookup.
    """
    pc = (postal_code or "").strip()
    if pc.startswith(tuple(str(prefix) for prefix in range(10, 20))):
        return REGION_ATTICA
    return "Other"


def calculate_shipping_cost(
    cart_items,
    cart_total,
    region,
    is_cash_on_delivery=False,
):
    """
    Compute the former weight-based courier shipping cost for a cart.

    Checkout no longer uses this for the customer-facing courier option
    (replaced by a flat fee). Kept for tests and as a reference tariff.

    Args:
        cart_items: Iterable of cart line objects. Each item must expose
            ``quantity`` and a related ``product`` (or ``product_variant.product``)
            with ``weight``, ``length``, ``width``, and ``height`` in Decimal.
        cart_total: Cart subtotal (products only, excluding shipping).
        region: Region label, e.g. ``REGION_ATTICA`` or ``"Other"``.
        is_cash_on_delivery: When True, the cash-on-delivery surcharge is added
            even if base shipping is free.

    Returns:
        Decimal: Final shipping cost in euros.
    """
    cart_total = Decimal(cart_total)

    # Free shipping for orders of €70+ (products subtotal, all regions).
    if cart_total >= Decimal(str(settings.FREE_SHIPPING_ORDER_MINIMUM)):
        shipping_cost = Decimal("0.00")
        if is_cash_on_delivery:
            shipping_cost += COD_FEE
        return shipping_cost

    total_real_weight = Decimal("0.00")
    total_volumetric_weight = Decimal("0.00")

    for item in cart_items:
        product = _resolve_product(item)
        quantity = Decimal(getattr(item, "quantity", 1))

        # Billable real weight accumulates per unit in the cart.
        total_real_weight += Decimal(product.weight) * quantity

        # Volumetric weight: (L × W × H cm) / 5000 → kg equivalent.
        item_volumetric_weight = (
            Decimal(product.length)
            * Decimal(product.width)
            * Decimal(product.height)
        ) / VOLUMETRIC_DIVISOR
        total_volumetric_weight += item_volumetric_weight * quantity

    # Couriers charge whichever is higher: actual or volumetric weight.
    chargeable_weight = max(total_real_weight, total_volumetric_weight)

    if chargeable_weight <= BASE_WEIGHT_LIMIT:
        shipping_cost = BASE_FEE
    else:
        # Partial kilograms round up to the next whole kg for surcharge bands.
        extra_kg = math.ceil(float(chargeable_weight - BASE_WEIGHT_LIMIT))
        shipping_cost = BASE_FEE + (Decimal(extra_kg) * EXTRA_KG_FEE)

    if is_cash_on_delivery:
        shipping_cost += COD_FEE

    return shipping_cost.quantize(Decimal("0.01"))


def _resolve_product(cart_item):
    """Return the Product instance from a cart line, regardless of item shape."""
    if hasattr(cart_item, "product_variant"):
        return cart_item.product_variant.product
    if hasattr(cart_item, "product"):
        return cart_item.product
    raise AttributeError(
        "Each cart item must provide product_variant or product for shipping."
    )
