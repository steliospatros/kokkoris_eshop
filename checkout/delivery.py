"""
Delivery-related helpers shared by the checkout views:

- is_within_athens_urban_area(): decides whether a given postal code is
  eligible for free company delivery (vs mandatory courier).
- calculate_courier_fee(): the single, centralized place where the courier
  fee is computed for a given address + chosen delivery method.

Keeping both of these as small, standalone functions (instead of scattering
this logic across views/templates) means that later, when real courier
pricing or a more precise area lookup is plugged in, only the body of these
two functions needs to change - nothing else in the checkout flow.
"""
from decimal import Decimal

from orders.models import Order
from products.catalog import format_decimal_greek
from products.utils import calculate_shipping_cost, postal_code_to_region

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
    address + chosen delivery method. Delegates to the ELTA tariff in
    products.utils.calculate_shipping_cost for courier shipments.
    """
    if delivery_method != Order.DELIVERY_METHOD_COURIER:
        return Decimal("0.00")

    if cart is None or cart_total is None:
        return Decimal("0.00")

    region = postal_code_to_region(postal_code)
    return calculate_shipping_cost(
        cart_items=cart.items if hasattr(cart, "items") else cart,
        cart_total=cart_total,
        region=region,
        is_cash_on_delivery=is_cash_on_delivery,
    )


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
    courier_total = cart_total + courier_fee
    options.append(
        {
            "value": Order.DELIVERY_METHOD_COURIER,
            "label": "Αποστολή μέσω ELTA",
            "description": (
                "Αποστολή με courier ELTA σε όλη την Ελλάδα."
                if not within_urban_area
                else "Εναλλακτικά, αποστολή με courier ELTA."
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
    return options, within_urban_area
