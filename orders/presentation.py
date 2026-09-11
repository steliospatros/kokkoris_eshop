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
    PAYMENT_STATE_LABELS,
)
from orders.models import Order
from products.catalog import format_decimal_greek, format_weight
from checkout.boxnow_webhooks import BOXNOW_EVENT_LABELS


MAX_DELIVERY_BUSINESS_DAYS = 3
COMPANY_PRIORITY_ORANGE_DAY = 2
DELIVERY_WINDOW_PHRASE = "έως 3 εργάσιμες ημέρες"
PRIORITY_GREEN = "green"
PRIORITY_ORANGE = "orange"
PRIORITY_RED = "red"
PRIORITY_CHOICES = (
    (PRIORITY_GREEN, "Πράσινες"),
    (PRIORITY_ORANGE, "Πορτοκαλί"),
    (PRIORITY_RED, "Κόκκινες"),
)


def add_business_days(start_day: date, business_days: int) -> date:
    """Add business days (Mon–Fri) to a calendar date."""
    current = start_day
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def business_days_elapsed(start_day: date, today: date) -> int:
    """Count weekdays from the day after start_day through today."""
    if today <= start_day:
        return 0
    elapsed = 0
    current = start_day
    while current < today:
        current += timedelta(days=1)
        if current.weekday() < 5:
            elapsed += 1
    return elapsed


def company_delivery_priority(order, today=None):
    """
    Age color for company (Athens) deliveries only.

    Green on days 0–1, orange on days 2–3, red after the 3rd business day.
    Courier and BOX NOW stay uncolored.
    """
    if getattr(order, "delivery_method", None) != Order.DELIVERY_METHOD_COMPANY:
        return ""
    if today is None:
        today = timezone.localdate()
    start = timezone.localtime(order.order_date).date()
    elapsed = business_days_elapsed(start, today)
    if elapsed > MAX_DELIVERY_BUSINESS_DAYS:
        return PRIORITY_RED
    if elapsed >= COMPANY_PRIORITY_ORANGE_DAY:
        return PRIORITY_ORANGE
    return PRIORITY_GREEN


def build_delivery_eta_message(order: Order) -> str:
    """Customer-facing ETA text based on order registration time."""
    registered_at = timezone.localtime(order.order_date)
    registered_label = registered_at.strftime("%d/%m/%Y στις %H:%M")
    eta_from = add_business_days(registered_at.date(), 1)
    eta_to = add_business_days(registered_at.date(), MAX_DELIVERY_BUSINESS_DAYS)
    eta_range = f"{eta_from.strftime('%d/%m/%Y')} – {eta_to.strftime('%d/%m/%Y')}"

    if order.delivery_method == Order.DELIVERY_METHOD_COMPANY:
        return (
            f"Δεδομένης της καταχώρησης στις {registered_label}, η παραγγελία σας "
            f"θα παραδοθεί εκτιμώμενες {eta_range} ({DELIVERY_WINDOW_PHRASE})."
        )

    if order.delivery_method == Order.DELIVERY_METHOD_BOX_NOW:
        locker = order.boxnow_locker_name or "το επιλεγμένο locker"
        tracking = BOXNOW_EVENT_LABELS.get(order.boxnow_last_event, "")
        pin_note = (
            f" PIN παραλαβής: {order.boxnow_parcel_pin}."
            if order.boxnow_parcel_pin
            else ""
        )
        status_note = f" {tracking}" if tracking else ""
        return (
            f"Δεδομένης της καταχώρησης στις {registered_label}, η παραγγελία σας "
            f"θα παραδοθεί στο BOX NOW locker «{locker}». Εκτιμώμενη παράδοση: "
            f"{eta_range} ({DELIVERY_WINDOW_PHRASE}).{status_note}{pin_note}"
        )

    return (
        f"Δεδομένης της καταχώρησης στις {registered_label}, μπορείτε να "
        f"παρακολουθήσετε την αποστολή μέσω courier. Εκτιμώμενη παράδοση: "
        f"{eta_range} ({DELIVERY_WINDOW_PHRASE})."
    )


def build_delivery_map_url(order: Order, *, size="640x320", zoom=16, scale=2):
    """Static map snapshot for the delivery coordinates."""
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return None
    lat = order.delivery_latitude
    lng = order.delivery_longitude
    if lat is None or lng is None:
        return None
    return (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lng}&zoom={zoom}&size={size}&scale={scale}"
        f"&markers=color:0x42746c%7C{lat},{lng}"
        f"&key={api_key}"
    )


def build_delivery_maps_link(order: Order):
    """Google Maps page centered on the delivery pin."""
    lat = order.delivery_latitude
    lng = order.delivery_longitude
    if lat is None or lng is None:
        return None
    return f"https://www.google.com/maps?q={lat},{lng}"


def build_order_item_rows(order: Order):
    """Line items with product images for templates."""
    rows = []
    for item in order.items.select_related("product_variant__product__company"):
        product = item.product_variant.product
        variant = item.product_variant
        company_name = product.company.name if product.company_id else ""
        display_name = f"{company_name} {product.name}".strip() if company_name else product.name
        image_url = None
        image_path = None
        if product.image:
            try:
                image_url = product.image.url
            except ValueError:
                image_url = None
            try:
                image_path = product.image.path
            except (ValueError, OSError):
                image_path = None
        rows.append(
            {
                "quantity": item.quantity,
                "name": display_name,
                "weight": variant.weight,
                "size_label": format_weight(variant.weight, variant.unit_label),
                "unit_price": item.price_at_purchase,
                "unit_price_display": format_decimal_greek(item.price_at_purchase),
                "line_total": item.line_total,
                "line_total_display": format_decimal_greek(item.line_total),
                "image_url": image_url,
                "image_path": image_path,
                "image_cid": "",
            }
        )
    return rows


def build_payment_display(order: Order):
    """
    How the customer pays and whether they still owe anything.

    Shared by the order list, the detail/confirmation pages and the emails so
    all four can never disagree about whether an order is settled.
    """
    state = order.payment_state()
    return {
        "payment_label": PAYMENT_METHOD_LABELS.get(
            order.payment_method, order.get_payment_method_display()
        ),
        "payment_state": state,
        "payment_state_label": PAYMENT_STATE_LABELS.get(state, ""),
        "payment_is_settled": order.payment_is_settled(),
    }


def build_order_detail_context(order: Order, *, show_success_banner=False):
    """Shared context for confirmation and order detail pages."""
    delivery_address_parts = [
        order.delivery_address,
        order.delivery_city,
        order.delivery_postal_code,
    ]
    if order.delivery_floor:
        delivery_address_parts.insert(1, order.delivery_floor)

    boxnow_locker_display = ""
    if order.delivery_method == Order.DELIVERY_METHOD_BOX_NOW and order.boxnow_locker_id:
        locker_parts = [
            order.boxnow_locker_name,
            order.boxnow_locker_address,
            order.boxnow_locker_postal_code,
        ]
        boxnow_locker_display = ", ".join(part for part in locker_parts if part)

    return {
        "order": order,
        "show_success_banner": show_success_banner,
        "status_label": ORDER_STATUS_LABELS.get(
            order.status, order.get_status_display()
        ),
        **build_payment_display(order),
        "delivery_label": DELIVERY_METHOD_LABELS.get(
            order.delivery_method, order.get_delivery_method_display()
        ),
        "order_code_display": order.public_code_display,
        "order_date_display": timezone.localtime(order.order_date).strftime(
            "%d/%m/%Y %H:%M"
        ),
        "eta_message": build_delivery_eta_message(order),
        "delivery_map_url": build_delivery_map_url(order),
        "delivery_address_display": ", ".join(
            part for part in delivery_address_parts if part
        ),
        "boxnow_locker_display": boxnow_locker_display,
        "is_boxnow_delivery": order.delivery_method == Order.DELIVERY_METHOD_BOX_NOW,
        "item_rows": build_order_item_rows(order),
        "customer_name": order.user.get_full_name() if order.user_id else "",
        "customer_email": order.user.email if order.user_id else "",
        "cart_cost_display": format_decimal_greek(order.cart_cost),
        "courier_fee_display": format_decimal_greek(order.courier_fee),
        "total_cost_display": format_decimal_greek(order.total_cost),
        "courier_fee_is_free": order.courier_fee == 0,
        "cancel_button_label": (
            "Αίτημα ακύρωσης & επιστροφής"
            if order.can_request_cancellation()
            else "Ακύρωση παραγγελίας"
        ),
        "cancellation_reason": (order.cancellation_reason or "").strip(),
        "cancel_confirm_message": (
            "Η ακύρωση θα εξεταστεί από την ομάδα μας. Μετά την επιβεβαίωση, "
            "θα επιστραφούν τα χρήματα στην κάρτα σου. Να συνεχίσω;"
            if order.can_request_cancellation()
            else "Είσαι σίγουρος/η ότι θέλεις να ακυρώσεις την παραγγελία;"
        ),
    }
