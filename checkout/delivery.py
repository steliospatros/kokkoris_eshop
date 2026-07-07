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


def calculate_courier_fee(postal_code, delivery_method):
    """
    Single, centralized place where the courier fee is computed for a given
    address + chosen delivery method. Every other part of the checkout flow
    (views, templates, Order creation) calls ONLY this function and never
    hardcodes a fee amount itself - this way, swapping the placeholder logic
    below for real courier pricing (flat zone rates, or a live rate lookup
    from an ACS / ELTA Courier / Geniki Taxydromiki API) later requires
    changing only this function's body, nothing else in the codebase.

    Current behaviour (placeholder, per explicit product decision): always
    returns 0, regardless of zone. Free company delivery is always 0 by
    definition.
    """
    if delivery_method != Order.DELIVERY_METHOD_COURIER:
        return Decimal("0.00")
    # TODO (later part): replace with real courier pricing once a specific
    # courier company/API is integrated. For now, intentionally flat 0.
    return Decimal("0.00")
