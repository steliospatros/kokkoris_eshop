"""Free-shipping promotion messaging for cart, checkout, and homepage."""
from decimal import Decimal

from django.conf import settings

from products.catalog import format_decimal_greek


def get_free_shipping_minimum():
    return Decimal(str(settings.FREE_SHIPPING_ORDER_MINIMUM))


def qualifies_for_free_shipping(cart_total):
    return Decimal(cart_total) >= get_free_shipping_minimum()


def format_amount_short(value):
    """Marketing-friendly amount: «60» instead of «60,00»."""
    amount = Decimal(value).quantize(Decimal("0.01"))
    if amount == amount.to_integral_value():
        return str(int(amount))
    return format_decimal_greek(amount)


def build_free_shipping_promo(cart_total):
    """
    Build template context for the free-shipping promotion.

    Returns headline, progress, and either a success message or how much
    remains to qualify (e.g. «Απομένουν ακόμα 35,00 €…»).
    """
    minimum = get_free_shipping_minimum()
    total = Decimal(cart_total)
    qualified = total >= minimum
    remaining = max(Decimal("0.00"), minimum - total)
    progress = (
        100
        if qualified
        else min(100, int((total / minimum) * 100)) if minimum > 0 else 0
    )

    if qualified:
        message = "Έχετε κερδίσει δωρεάν μεταφορικά!"
        detail = f"Η παραγγελία σας ξεπερνά τα {format_decimal_greek(minimum)} €."
    else:
        message = (
            f"Απομένουν ακόμα {format_decimal_greek(remaining)} € "
            "για να αποκτήσετε δωρεάν μεταφορικά."
        )
        detail = (
            f"Δωρεάν μεταφορικά για παραγγελίες από "
            f"{format_decimal_greek(minimum)} € και άνω."
        )

    return {
        "qualified": qualified,
        "is_static": False,
        "minimum": minimum,
        "minimum_display": format_decimal_greek(minimum),
        "minimum_short": format_amount_short(minimum),
        "remaining": remaining,
        "remaining_display": format_decimal_greek(remaining),
        "remaining_short": format_amount_short(remaining),
        "cart_total": total,
        "cart_total_display": format_decimal_greek(total),
        "progress_percent": progress,
        "headline": (
            f"Δωρεάν μεταφορικά για παραγγελίες άνω των "
            f"{format_decimal_greek(minimum)} €"
        ),
        "strip_headline": f"Δωρεάν μεταφορικά άνω των {format_amount_short(minimum)}€",
        "message": message,
        "detail": detail,
    }


def build_static_free_shipping_promo():
    """Homepage banner when the cart is empty (no progress to show)."""
    minimum = get_free_shipping_minimum()
    return {
        "qualified": False,
        "is_static": True,
        "minimum": minimum,
        "minimum_display": format_decimal_greek(minimum),
        "minimum_short": format_amount_short(minimum),
        "remaining": minimum,
        "remaining_display": format_decimal_greek(minimum),
        "remaining_short": format_amount_short(minimum),
        "progress_percent": 0,
        "headline": (
            f"Δωρεάν μεταφορικά για παραγγελίες άνω των "
            f"{format_decimal_greek(minimum)} €"
        ),
        "strip_headline": f"Δωρεάν μεταφορικά άνω των {format_amount_short(minimum)}€",
        "message": "Σε όλη την Ελλάδα, με courier ή BOX NOW locker.",
        "detail": (
            f"Συμπληρώστε το καλάθι σας με "
            f"{format_decimal_greek(minimum)} € και κερδίστε δωρεάν αποστολή."
        ),
    }
