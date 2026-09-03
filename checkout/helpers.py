"""Helpers shared across checkout steps."""
from decimal import Decimal

from django.urls import reverse

from cart.presentation import build_cart_summary
from orders.models import Order
from products.catalog import format_decimal_greek

CHECKOUT_STEP_ADDRESS = "address"
CHECKOUT_STEP_DELIVERY = "delivery"
CHECKOUT_STEP_PAYMENT = "payment"

CHECKOUT_STEP_ORDER = (
    CHECKOUT_STEP_ADDRESS,
    CHECKOUT_STEP_DELIVERY,
    CHECKOUT_STEP_PAYMENT,
)

CHECKOUT_STEP_LABELS = {
    CHECKOUT_STEP_ADDRESS: "Διεύθυνση παράδοσης",
    CHECKOUT_STEP_DELIVERY: "Τρόπος αποστολής",
    CHECKOUT_STEP_PAYMENT: "Τρόπος πληρωμής",
}

CHECKOUT_STEP_URLS = {
    CHECKOUT_STEP_ADDRESS: "checkout:address",
    CHECKOUT_STEP_DELIVERY: "checkout:delivery",
    CHECKOUT_STEP_PAYMENT: "checkout:payment",
}

DELIVERY_METHOD_LABELS = {
    Order.DELIVERY_METHOD_COMPANY: "Δωρεάν παράδοση από υπάλληλο",
    Order.DELIVERY_METHOD_COURIER: "Αποστολή με courier",
    Order.DELIVERY_METHOD_BOX_NOW: "BOX NOW locker",
}


def build_checkout_sidebar(cart, *, courier_fee=None, show_shipping_breakdown=False):
    summary = build_cart_summary(cart)
    fee = courier_fee if courier_fee is not None else Decimal("0.00")
    grand_total = summary["total"] + fee
    return {
        "cart_lines": summary["lines"],
        "cart_total": summary["total"],
        "cart_total_display": summary["total_display"],
        "cart_total_items": summary["total_items"],
        "courier_fee": fee,
        "courier_fee_display": format_decimal_greek(fee),
        "checkout_grand_total_display": format_decimal_greek(grand_total),
        "show_shipping_breakdown": show_shipping_breakdown,
    }


def build_checkout_steps(current_step, checkout_data=None):
    """Vertical step list for checkout — each step unlocks after the previous."""
    checkout_data = checkout_data or {}

    address_summary = ""
    if checkout_data.get("address"):
        address_summary = (
            f"{checkout_data['address']}, {checkout_data.get('city', '')} "
            f"{checkout_data.get('postal_code', '')}"
        ).strip()

    delivery_summary = ""
    delivery_method = checkout_data.get("delivery_method")
    if delivery_method:
        delivery_summary = DELIVERY_METHOD_LABELS.get(delivery_method, delivery_method)
        if delivery_method == Order.DELIVERY_METHOD_BOX_NOW and checkout_data.get(
            "boxnow_locker_name"
        ):
            delivery_summary = (
                f"{delivery_summary} — {checkout_data['boxnow_locker_name']}"
            )

    summaries = {
        CHECKOUT_STEP_ADDRESS: address_summary,
        CHECKOUT_STEP_DELIVERY: delivery_summary,
        CHECKOUT_STEP_PAYMENT: "",
    }

    steps = []
    for index, step_key in enumerate(CHECKOUT_STEP_ORDER, start=1):
        if step_key == current_step:
            state = "active"
        elif step_key == CHECKOUT_STEP_ADDRESS and checkout_data and current_step != CHECKOUT_STEP_ADDRESS:
            state = "completed"
        elif (
            step_key == CHECKOUT_STEP_DELIVERY
            and delivery_method
            and current_step == CHECKOUT_STEP_PAYMENT
        ):
            state = "completed"
        else:
            state = "locked"

        steps.append(
            {
                "key": step_key,
                "number": index,
                "label": CHECKOUT_STEP_LABELS[step_key],
                "state": state,
                "summary": summaries[step_key],
                "url": reverse(CHECKOUT_STEP_URLS[step_key]) if state == "completed" else "",
            }
        )
    return steps


def format_delivery_address(user):
    parts = [user.street, user.street_number]
    line = " ".join(part for part in parts if part).strip()
    return line or (user.address or "")


def stash_checkout_address(request, user):
    request.session[SESSION_KEY] = {
        "phone_number": user.phone_number,
        "city": user.city,
        "address": format_delivery_address(user),
        "postal_code": user.postal_code,
        "floor": user.floor or "",
        "latitude": "" if user.latitude is None else str(user.latitude),
        "longitude": "" if user.longitude is None else str(user.longitude),
        "delivery_notes": user.delivery_notes or "",
    }


SESSION_KEY = "checkout_data"
