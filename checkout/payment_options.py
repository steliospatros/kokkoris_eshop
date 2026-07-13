"""Payment method presentation for checkout step 3."""

from decimal import Decimal

from orders.models import Order
from products.catalog import format_decimal_greek
from products.utils import COD_FEE


def build_payment_options(
    *,
    base_courier_fee,
    cod_courier_fee,
    cart_total,
):
    """
    Payment choices for checkout step 3.

    Each option includes a short label, an explanatory note shown when selected,
    and optional pricing metadata for the sidebar (COD surcharge on shipping).
    """
    cod_surcharge = max(Decimal("0.00"), cod_courier_fee - base_courier_fee)
    cod_surcharge_display = format_decimal_greek(cod_surcharge)

    return [
        {
            "value": Order.PAYMENT_METHOD_COD,
            "label": "Αντικαταβολή",
            "description": (
                "Πληρώνεις με μετρητά ή μέσω POS στον διανομέα κατά την παράδοση. "
                "Ιδανικό αν προτιμάς να δεις πρώτα την παραγγελία σου."
            ),
            "note": (
                f"Ισχύει επιπλέον χρέωση αντικαταβολής {format_decimal_greek(COD_FEE)} € "
                "στην αποστολή με courier."
                if cod_surcharge > 0
                else "Δεν υπάρχει επιπλέον χρέωση αντικαταβολής για την επιλεγμένη αποστολή."
            ),
            "cod_surcharge": cod_surcharge,
            "cod_surcharge_display": cod_surcharge_display,
            "total_with_surcharge": format_decimal_greek(cart_total + cod_courier_fee),
        },
        {
            "value": Order.PAYMENT_METHOD_CARD,
            "label": "Πληρωμή μέσω κάρτας",
            "description": (
                "Ολοκληρώνεις την πληρωμή online με ασφάλεια μέσω Stripe. "
                "Δέχονται Visa, Mastercard, Maestro και άλλες κάρτες."
            ),
            "note": (
                "Τα στοιχεία της κάρτας εισάγονται στο προστατευμένο περιβάλλον Stripe — "
                "δεν αποθηκεύονται στον server μας."
            ),
            "cod_surcharge": Decimal("0.00"),
            "cod_surcharge_display": format_decimal_greek(Decimal("0.00")),
            "total_with_surcharge": format_decimal_greek(cart_total + base_courier_fee),
        },
    ]
