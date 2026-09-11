"""Courier deliveries queue — grouped by method, company delivery first."""
from django.db import transaction
from django.utils import timezone

from administration.order_actions import cancel_order_by_admin
from administration.order_queries import (
    DELIVERY_ALL,
    DELIVERY_BOX_NOW,
    DELIVERY_COMPANY,
    DELIVERY_COURIER,
    DELIVERY_FILTER_CHOICES,
    apply_delivery_filter,
    build_order_row,
)
from orders.models import Order
from orders.presentation import PRIORITY_CHOICES, company_delivery_priority


SHOW_PENDING = "pending"
SHOW_DELIVERED = "delivered"

SHOW_CHOICES = (
    (SHOW_PENDING, "Προς παράδοση"),
    (SHOW_DELIVERED, "Παραδομένες"),
)

PENDING_STATUSES = Order.IN_PROGRESS_STATUSES

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
        row["payment_state"] = order.payment_state()
        row["payment_is_settled"] = order.payment_is_settled()
        row["priority"] = (
            company_delivery_priority(order) if order.status != Order.STATUS_DELIVERED else ""
        )
        rows.append(row)
    return rows


def group_delivery_rows(rows, *, priority=""):
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
        orders = by_method[group["method"]]
        if priority and group["key"] == "company":
            orders = [row for row in orders if row.get("priority") == priority]
        grouped.append(
            {
                "key": group["key"],
                "label": group["label"],
                "method": group["method"],
                "orders": orders,
                "count": len(orders),
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


def build_deliveries_panel_context(
    *, show=SHOW_PENDING, priority="", delivery_filter=DELIVERY_COMPANY
):
    if show not in {SHOW_PENDING, SHOW_DELIVERED}:
        show = SHOW_PENDING
    allowed = {key for key, _label in PRIORITY_CHOICES}
    if priority not in allowed:
        priority = ""
    if delivery_filter not in {key for key, _label in DELIVERY_FILTER_CHOICES}:
        delivery_filter = DELIVERY_COMPANY

    qs = apply_delivery_filter(_deliveries_queryset(), delivery_filter)
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
    priority_counts = {key: 0 for key, _label in PRIORITY_CHOICES}
    for row in rows:
        key = row.get("priority")
        if key in priority_counts:
            priority_counts[key] += 1

    groups = group_delivery_rows(rows, priority=priority)
    if delivery_filter != DELIVERY_ALL:
        wanted = {
            DELIVERY_COMPANY: Order.DELIVERY_METHOD_COMPANY,
            DELIVERY_COURIER: Order.DELIVERY_METHOD_COURIER,
            DELIVERY_BOX_NOW: Order.DELIVERY_METHOD_BOX_NOW,
        }.get(delivery_filter)
        groups = [group for group in groups if group.get("method") == wanted]

    return {
        "show": show,
        "show_choices": SHOW_CHOICES,
        "priority": priority,
        "priority_choices": PRIORITY_CHOICES,
        "priority_counts": priority_counts,
        "pending_count": pending_count,
        "delivered_count": delivered_count,
        "orders": rows,
        "delivery_groups": groups,
        "orders_count": len(rows),
        "is_pending_view": show == SHOW_PENDING,
        "delivery_filter": delivery_filter,
        "delivery_filter_choices": DELIVERY_FILTER_CHOICES,
    }


def status_after_undeliver(order):
    """Restore a registered order when staff undo a delivery mark."""
    return Order.STATUS_NEW


def apply_delivery_action(order, *, action, collected_payment="", reason=""):
    """Courier actions on the deliveries page: deliver, undo, or cancel."""
    action = (action or "").strip()
    if action == "deliver":
        return mark_order_delivery(
            order,
            delivered=True,
            collected_payment=collected_payment,
        )
    if action == "undeliver":
        return mark_order_delivery(order, delivered=False, reason=reason)
    if action == "cancel":
        if order.status != Order.STATUS_DELIVERED:
            return False, "Ακύρωση από εδώ γίνεται μόνο σε παραδομένη παραγγελία."
        return cancel_order_by_admin(order, reason)
    return False, "Άγνωστη ενέργεια."


def mark_order_delivery(order, *, delivered, collected_payment="", reason=""):
    """
    Mark an order delivered or undo that mark.

    Door collections require cash vs card. Undoing a delivery needs a written
    reason so an accidental tap cannot silently rewind the order. Uses .save()
    so the customer email fires.
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
    reason = (reason or "").strip()
    if len(reason) < 3:
        return False, "Γράψε γιατί αναιρείται η παράδοση (τουλάχιστον 3 χαρακτήρες)."
    stamp = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    note = f"Αναίρεση παράδοσης ({stamp}): {reason}"
    order.special_notes = (
        f"{order.special_notes.rstrip()}\n{note}" if order.special_notes else note
    )
    order.status = status_after_undeliver(order)
    order.delivered_at = None
    update_fields = ["status", "delivered_at", "special_notes"]
    # Stripe money stays recorded: only door collections can be un-declared.
    if not order.payment_is_locked():
        order.collected_payment_method = ""
        update_fields.append("collected_payment_method")
    with transaction.atomic():
        order.save(update_fields=update_fields)
    return True, f"Η παραγγελία {order.public_code_display} επέστρεψε στις εκκρεμείς."
