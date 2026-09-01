"""
Delivery-related helpers shared by the checkout views:

- is_within_athens_urban_area(): decides whether a given postal code is
  eligible for free company delivery (vs mandatory courier).
- calculate_courier_fee(): the single, centralized place where the courier
  fee is computed for a given address + chosen delivery method.

Keeping both of these as small, standalone functions (instead of scattering
this logic across views/templates) means that later, when a real carrier
is chosen, only the body of calculate_courier_fee needs to change.
"""
from decimal import Decimal

from django.conf import settings

from checkout.boxnow_pricing import (
    COMPARTMENT_LABELS,
    calculate_boxnow_shipping_cost,
    determine_compartment_size,
    exceeds_boxnow_weight_limit,
)
from orders.models import Order
from products.catalog import format_decimal_greek
from products.utils import COD_FEE, postal_code_to_region

# Postal codes (T.K.) starting with one of these prefixes are treated as
# being within the broader Athens urban area: Athens, Piraeus, and all
# contiguous suburbs (Peristeri, Kallithea, Nikaia, Kifisia, Marousi,
# Glyfada, etc.) - i.e. "the idea of the city of Athens" in everyday speech,
# not just the narrow Athens/Piraeus municipalities, but also not the whole
# Attica prefecture. Postal codes starting with "19" (and anything not
# starting with "1") are treated as outlying Attica areas (Rafina,
# Marathonas, Lavrio, Megara, Saronic islands) or entirely different
# regions, where courier delivery is mandatory.
#
# This is a practical approximation, NOT an exact municipal boundary lookup
# - kept as a simple, easily-editable constant so it can be adjusted later
# if a specific area is found to be misclassified.
ATHENS_URBAN_AREA_PREFIXES = tuple(str(p) for p in range(10, 19))  # "10".."18"


def is_within_athens_urban_area(postal_code):
    """Returns True if the given postal code is within the Athens urban area."""
    pc = (postal_code or "").strip()
    return pc.startswith(ATHENS_URBAN_AREA_PREFIXES)


def calculate_courier_fee(
    postal_code,
    delivery_method,
    *,
    cart=None,
    cart_total=None,
    is_cash_on_delivery=False,
):
    """
    Single, centralized place where the courier fee is computed for a given
    address + chosen delivery method.

    Door-delivery courier uses settings.COURIER_FLAT_FEE (default 5.00 €)
    below the free-shipping threshold. BOX NOW keeps its own size/weight
    pricing. Cash-on-delivery still adds the existing COD surcharge.
    """
    if cart is None or cart_total is None:
        return Decimal("0.00")

    region = postal_code_to_region(postal_code)
    cart_items = cart.items if hasattr(cart, "items") else cart

    if delivery_method == Order.DELIVERY_METHOD_COURIER:
        cart_total = Decimal(cart_total)
        if cart_total >= Decimal(str(settings.FREE_SHIPPING_ORDER_MINIMUM)):
            shipping_cost = Decimal("0.00")
        else:
            shipping_cost = Decimal(str(settings.COURIER_FLAT_FEE))
        if is_cash_on_delivery:
            shipping_cost += COD_FEE
        return shipping_cost.quantize(Decimal("0.01"))

    if delivery_method == Order.DELIVERY_METHOD_BOX_NOW:
        return calculate_boxnow_shipping_cost(
            cart_items=cart_items,
            cart_total=cart_total,
            region=region,
        )

    return Decimal("0.00")


def build_delivery_options(*, cart_total, postal_code, cart=None):
    """Shipping choices for checkout step 2."""
    within_urban_area = is_within_athens_urban_area(postal_code)
    options = []

    # Company delivery is always shown first; it is only selectable inside the
    # Athens urban area (postal codes 10x–18x).
    options.append(
        {
            "value": Order.DELIVERY_METHOD_COMPANY,
            "label": "Παράδοση από υπάλληλο",
            "description": "Παράδοση στην πόρτα σου σε 3–4 εργάσιμες ημέρες.",
            "fee": Decimal("0.00"),
            "fee_display": "Δωρεάν",
            "total": cart_total,
            "total_display": format_decimal_greek(cart_total),
            "disabled": not within_urban_area,
            "unavailable_message": (
                "Η παράδοση από υπάλληλο δεν πραγματοποιείται για την περιοχή που έχετε δηλώσει"
                if not within_urban_area
                else ""
            ),
        }
    )

    courier_fee = calculate_courier_fee(
        postal_code,
        Order.DELIVERY_METHOD_COURIER,
        cart=cart,
        cart_total=cart_total,
    )
    from products.shipping_promo import get_free_shipping_minimum

    free_minimum = get_free_shipping_minimum()
    courier_total = cart_total + courier_fee
    free_note = (
        f" (δωρεάν μεταφορικά — η παραγγελία σας ξεπερνά τα {format_decimal_greek(free_minimum)} €)"
        if courier_fee == 0 and cart_total >= free_minimum
        else ""
    )
    courier_desc_base = (
        "Αποστολή με courier σε όλη την Ελλάδα"
        if not within_urban_area
        else "Εναλλακτικά, αποστολή με courier"
    )
    options.append(
        {
            "value": Order.DELIVERY_METHOD_COURIER,
            "label": "Αποστολή με courier",
            "description": (
                f"{courier_desc_base}. "
                f"Σταθερή χρέωση αποστολής"
                f"{free_note}."
            ),
            "fee": courier_fee,
            "fee_display": (
                f"+{format_decimal_greek(courier_fee)} €"
                if courier_fee
                else "Δωρεάν"
            ),
            "total": courier_total,
            "total_display": format_decimal_greek(courier_total),
            "disabled": False,
            "unavailable_message": "",
        }
    )

    if settings.BOXNOW_WIDGET_ENABLED:
        cart_items = cart.items if cart and hasattr(cart, "items") else (cart or [])
        too_heavy = exceeds_boxnow_weight_limit(cart_items)
        compartment = determine_compartment_size(cart_items)
        boxnow_fee = calculate_courier_fee(
            postal_code,
            Order.DELIVERY_METHOD_BOX_NOW,
            cart=cart,
            cart_total=cart_total,
        )
        boxnow_total = cart_total + boxnow_fee
        compartment_label = COMPARTMENT_LABELS.get(compartment, "")
        options.append(
            {
                "value": Order.DELIVERY_METHOD_BOX_NOW,
                "label": "Παράδοση σε BOX NOW locker",
                "description": (
                    f"Παράλαβε από αυτόματο locker BOX NOW (θήκη {compartment_label}). "
                    "Επίλεξε σημείο παραλαβής στον χάρτη."
                    if not too_heavy
                    else "Μη διαθέσιμο — το βάρος της παραγγελίας υπερβαίνει τα όρια του BOX NOW."
                ),
                "fee": boxnow_fee,
                "fee_display": (
                    f"+{format_decimal_greek(boxnow_fee)} €"
                    if boxnow_fee
                    else "Δωρεάν"
                ),
                "total": boxnow_total,
                "total_display": format_decimal_greek(boxnow_total),
                "disabled": too_heavy,
                "unavailable_message": (
                    "Το βάρος της παραγγελίας υπερβαίνει τα όρια του BOX NOW. "
                    "Επιλέξτε αποστολή με courier."
                    if too_heavy
                    else ""
                ),
                "requires_locker": not too_heavy,
                "compartment_size": compartment,
            }
        )

    return options, within_urban_area
