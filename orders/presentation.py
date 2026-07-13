"""
Presentation helpers for order history and order detail pages.
"""
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from accounts.profile_labels import (
    DELIVERY_METHOD_LABELS,
    ORDER_STATUS_LABELS,
    PAYMENT_METHOD_LABELS,
)
from orders.models import Order
from products.catalog import format_decimal_greek


def add_business_days(start_day: date, business_days: int) -> date:
    """Add business days (Mon–Fri) to a calendar date."""
    current = start_day
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def build_delivery_eta_message(order: Order) -> str:
    """Customer-facing ETA text based on order registration time."""
    registered_at = timezone.localtime(order.order_date)
    registered_label = registered_at.strftime("%d/%m/%Y στις %H:%M")
    eta_from = add_business_days(registered_at.date(), 3)
    eta_to = add_business_days(registered_at.date(), 4)
    eta_range = f"{eta_from.strftime('%d/%m/%Y')} – {eta_to.strftime('%d/%m/%Y')}"

    if order.delivery_method == Order.DELIVERY_METHOD_COMPANY:
        return (
            f"Δεδομένης της καταχώρησης στις {registered_label}, η παραγγελία σας "
            f"θα παραδοθεί εκτιμώμενες {eta_range} (3–4 εργάσιμες ημέρες)."
        )

    return (
        f"Δεδομένης της καταχώρησης στις {registered_label}, μπορείτε να "
        f"παρακολουθήσετε την αποστολή μέσω courier ELTA. Εκτιμώμενη παράδοση: "
        f"{eta_range} (3–4 εργάσιμες ημέρες)."
    )


def build_delivery_map_url(order: Order):
    """Static map snapshot for the delivery coordinates."""
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return None
    lat = order.delivery_latitude
    lng = order.delivery_longitude
    return (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lng}&zoom=16&size=640x320&scale=2"
        f"&markers=color:0x42746c%7C{lat},{lng}"
        f"&key={api_key}"
    )


def build_order_item_rows(order: Order):
    """Line items with product images for templates."""
    rows = []
    for item in order.items.select_related("product_variant__product"):
        product = item.product_variant.product
        rows.append(
            {
                "quantity": item.quantity,
                "name": product.name,
                "weight": item.product_variant.weight,
                "unit_price": item.price_at_purchase,
                "unit_price_display": format_decimal_greek(item.price_at_purchase),
                "line_total": item.line_total,
                "line_total_display": format_decimal_greek(item.line_total),
                "image_url": product.image.url if product.image else None,
            }
        )
    return rows


def build_order_detail_context(order: Order, *, show_success_banner=False):
    """Shared context for confirmation and order detail pages."""
    delivery_address_parts = [
        order.delivery_address,
        order.delivery_city,
        order.delivery_postal_code,
    ]
    if order.delivery_floor:
        delivery_address_parts.insert(1, order.delivery_floor)

    return {
        "order": order,
        "show_success_banner": show_success_banner,
        "status_label": ORDER_STATUS_LABELS.get(
            order.status, order.get_status_display()
        ),
        "payment_label": PAYMENT_METHOD_LABELS.get(
            order.payment_method, order.get_payment_method_display()
        ),
        "delivery_label": DELIVERY_METHOD_LABELS.get(
            order.delivery_method, order.get_delivery_method_display()
        ),
        "order_date_display": timezone.localtime(order.order_date).strftime(
            "%d/%m/%Y %H:%M"
        ),
        "eta_message": build_delivery_eta_message(order),
        "delivery_map_url": build_delivery_map_url(order),
        "delivery_address_display": ", ".join(
            part for part in delivery_address_parts if part
        ),
        "item_rows": build_order_item_rows(order),
        "cart_cost_display": format_decimal_greek(order.cart_cost),
        "courier_fee_display": format_decimal_greek(order.courier_fee),
        "total_cost_display": format_decimal_greek(order.total_cost),
        "courier_fee_is_free": order.courier_fee == 0,
    }
