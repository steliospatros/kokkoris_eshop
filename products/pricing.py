"""Shop price rounding: always the next tenth of a euro (0.85 → 0.90)."""

from decimal import ROUND_CEILING, Decimal

CENT = Decimal("0.01")
TENTH = Decimal("0.1")


def ceil_to_tenth(value):
    """Round a euro amount up to the next 0.10. Zero and empty stay 0.00."""
    if value is None:
        return None
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    if amount <= 0:
        return Decimal("0.00")
    return amount.quantize(TENTH, rounding=ROUND_CEILING).quantize(CENT)
