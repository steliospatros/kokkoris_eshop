"""Courier deliveries queue — grouped by method, company delivery first."""
from django.db import transaction
from django.utils import timezone

from administration.order_queries import build_order_row
from orders.models import Order


SHOW_PENDING = "pending"
SHOW_DELIVERED = "delivered"

SHOW_CHOICES = (
    (SHOW_PENDING, "Προς παράδοση"),
    (SHOW_DELIVERED, "Παραδομένες"),
)

PENDING_STATUSES = (
    Order.STATUS_NEW,
    Order.STATUS_PENDING,
    Order.STATUS_PAID,
)

# Company delivery (Athens) first — highest operational priority.
DELIVERY_GROUPS = (
    {
        "key": "company",
        "label": "Παράδοση από την εταιρία (εντός Αθηνών)",
        "method": Order.DELIVERY_METHOD_COMPANY,
    },
    {
        "key": "courier",
        "label": "Courier",
        "method": Order.DELIVERY_METHOD_COURIER,
    },
    {
        "key": "boxnow",
        "label": "BOX NOW",
        "method": Order.DELIVERY_METHOD_BOX_NOW,
    },
)


def _deliveries_queryset():
    return Order.objects.select_related("user").prefetch_related(
        "items__product_variant__product__company"
    )


def _order_rows(orders):
    rows = []
    for order in orders:
        row = build_order_row(order)
        row["is_delivered"] = order.status == Order.STATUS_DELIVERED
        row["can_toggle_delivery"] = True
        row["is_prepaid_card"] = order.is_prepaid_card()
        row["needs_collection_declaration"] = order.needs_collection_declaration()
        row["collected_payment_method"] = order.collected_payment_method
        rows.append(row)
    return rows


def group_delivery_rows(rows):
    """Split rows into company / courier / BOX NOW. Empty groups are kept."""
    by_method = {group["method"]: [] for group in DELIVERY_GROUPS}
    leftover = []
    for row in rows:
        method = row.get("delivery_method")
        if method in by_method:
            by_method[method].append(row)
        else:
            leftover.append(row)

    grouped = []
    for group in DELIVERY_GROUPS:
        grouped.append(
            {
                "key": group["key"],
                "label": group["label"],
                "orders": by_method[group["method"]],
                "count": len(by_method[group["method"]]),
            }
        )
    if leftover:
        grouped.append(
            {
                "key": "other",
                "label": "Άλλος τρόπος",
                "orders": leftover,
                "count": len(leftover),
            }
        )
    return grouped


def build_deliveries_panel_context(*, show=SHOW_PENDING):
    if show not in {SHOW_PENDING, SHOW_DELIVERED}:
        show = SHOW_PENDING

    qs = _deliveries_queryset()
    pending_count = qs.filter(status__in=PENDING_STATUSES).count()
    delivered_count = qs.filter(status=Order.STATUS_DELIVERED).count()

    if show == SHOW_DELIVERED:
        orders = list(
            qs.filter(status=Order.STATUS_DELIVERED).order_by("order_date")[:500]
        )
    else:
        orders = list(
            qs.filter(status__in=PENDING_STATUSES).order_by("order_date")[:500]
        )

    rows = _order_rows(orders)
    return {
        "show": show,
        "show_choices": SHOW_CHOICES,
        "pending_count": pending_count,
        "delivered_count": delivered_count,
        "orders": rows,
        "delivery_groups": group_delivery_rows(rows),
        "orders_count": len(rows),
        "is_pending_view": show == SHOW_PENDING,
    }


def status_after_undeliver(order):
    """Restore a workable status when a courier undoes a delivery mark."""
    if (
        order.payment_method == Order.PAYMENT_METHOD_CARD
        and order.stripe_payment_intent_id
    ):
        return Order.STATUS_PAID
    return Order.STATUS_NEW


def mark_order_delivery(order, *, delivered, collected_payment=""):
    """
    Mark an order delivered or undo that mark.

    Door collections require cash vs card. Uses .save() so the customer email fires.
    """
    if delivered:
        if order.status == Order.STATUS_DELIVERED:
            return False, "Η παραγγελία είναι ήδη παραδομένη."
        if order.status in (
            Order.STATUS_CANCELLED,
            Order.STATUS_FAILED,
            Order.STATUS_CANCELLATION_REQUESTED,
        ):
            return False, "Αυτή η παραγγελία δεν μπορεί να σημειωθεί ως παραδομένη."
        if order.needs_collection_declaration():
            if collected_payment not in (
                Order.PAYMENT_METHOD_CARD,
                Order.PAYMENT_METHOD_COD,
            ):
                return False, "Δήλωσε αν η πληρωμή έγινε με μετρητά ή κάρτα."
            order.collected_payment_method = collected_payment
        else:
            order.collected_payment_method = Order.PAYMENT_METHOD_CARD
        order.status = Order.STATUS_DELIVERED
        order.delivered_at = timezone.now()
        with transaction.atomic():
            order.save(
                update_fields=["status", "collected_payment_method", "delivered_at"]
            )
        return True, f"Η παραγγελία {order.public_code_display} σημειώθηκε ως παραδομένη."

    if order.status != Order.STATUS_DELIVERED:
        return False, "Η παραγγελία δεν είναι παραδομένη."
    order.status = status_after_undeliver(order)
    order.collected_payment_method = ""
    order.delivered_at = None
    with transaction.atomic():
        order.save(
            update_fields=["status", "collected_payment_method", "delivered_at"]
        )
    return True, f"Η παραγγελία {order.public_code_display} επέστρεψε στις εκκρεμείς."
