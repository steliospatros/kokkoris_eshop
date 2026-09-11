"""Admin actions on the shop orders panel: cancel, mark paid, set status."""
from django.db import transaction
from django.utils import timezone

from accounts.profile_labels import ORDER_STATUS_LABELS
from checkout.stripe_service import StripeNotConfiguredError
from orders.models import Order
from orders.refunds import (
    StripeRefundError,
    create_stripe_refund_for_order,
    order_requires_stripe_refund,
)


ADMIN_STATUS_CHOICES = (
    (Order.STATUS_NEW, str(ORDER_STATUS_LABELS[Order.STATUS_NEW])),
    (Order.STATUS_DELIVERED, str(ORDER_STATUS_LABELS[Order.STATUS_DELIVERED])),
    (
        Order.STATUS_CANCELLATION_REQUESTED,
        str(ORDER_STATUS_LABELS[Order.STATUS_CANCELLATION_REQUESTED]),
    ),
    (Order.STATUS_CANCELLED, str(ORDER_STATUS_LABELS[Order.STATUS_CANCELLED])),
)
PAYMENT_CHOICES = (
    (Order.PAYMENT_METHOD_COD, "Μετρητά"),
    (Order.PAYMENT_METHOD_CARD, "Κάρτα"),
)

ACTION_CANCEL = "cancel"
ACTION_MARK_PAID = "mark_paid"
ACTION_SET_STATUS = "set_status"


def _safe_next_url(next_url):
    if next_url and next_url.startswith("/administration/orders"):
        return next_url
    return ""


def cancel_order_by_admin(order, reason):
    reason = (reason or "").strip()
    if len(reason) < 3:
        return False, "Γράψε τον λόγο ακύρωσης (τουλάχιστον 3 χαρακτήρες)."
    if order.status == Order.STATUS_CANCELLED:
        return False, "Η παραγγελία είναι ήδη ακυρωμένη."

    refund_note = ""
    stripe_refund_id = order.stripe_refund_id
    if order_requires_stripe_refund(order):
        try:
            refund = create_stripe_refund_for_order(order)
            stripe_refund_id = refund.id
        except (StripeRefundError, StripeNotConfiguredError) as exc:
            refund_note = f" Η επιστροφή Stripe δεν έγινε: {exc}"

    order.cancellation_reason = reason
    order.status = Order.STATUS_CANCELLED
    order.stripe_refund_id = stripe_refund_id
    update_fields = ["status", "cancellation_reason", "stripe_refund_id"]
    with transaction.atomic():
        order.save(update_fields=update_fields)
    return True, (
        f"Η παραγγελία {order.public_code_display} ακυρώθηκε.{refund_note}"
    )


def mark_order_paid(order, payment_method):
    if order.payment_is_locked():
        return False, (
            "Η παραγγελία έχει εξοφληθεί με κάρτα μέσω Stripe — "
            "η πληρωμή δεν αλλάζει."
        )
    if payment_method not in (
        Order.PAYMENT_METHOD_CARD,
        Order.PAYMENT_METHOD_COD,
    ):
        return False, "Διάλεξε τρόπο πληρωμής (μετρητά ή κάρτα)."
    if order.status in (Order.STATUS_CANCELLED, Order.STATUS_FAILED):
        return False, "Η ακυρωμένη παραγγελία δεν μπορεί να δεχθεί είσπραξη."

    # payment_method is the customer's checkout choice and never changes here:
    # an αντικαταβολή collected by card at the door stays an αντικαταβολή.
    order.collected_payment_method = payment_method
    with transaction.atomic():
        order.save(update_fields=["collected_payment_method"])
    return True, (
        f"Η είσπραξη για την παραγγελία {order.public_code_display} καταχωρήθηκε."
    )


def set_order_status(order, status, *, cancellation_reason=""):
    allowed = {key for key, _label in ADMIN_STATUS_CHOICES}
    if status not in allowed:
        return False, "Μη έγκυρη κατάσταση παραγγελίας."
    if status == Order.STATUS_CANCELLED:
        return cancel_order_by_admin(order, cancellation_reason)
    if order.status == status:
        return False, "Η παραγγελία έχει ήδη αυτή την κατάσταση."

    previous_status = order.status
    if status == Order.STATUS_DELIVERED and not order.delivered_at:
        order.delivered_at = timezone.now()
    elif (
        previous_status == Order.STATUS_DELIVERED
        and status != Order.STATUS_DELIVERED
    ):
        order.delivered_at = None
    order.status = status
    update_fields = ["status", "delivered_at"]
    with transaction.atomic():
        order.save(update_fields=update_fields)
    return True, (
        f"Η κατάσταση της παραγγελίας {order.public_code_display} "
        f"άλλαξε σε «{ORDER_STATUS_LABELS.get(status, status)}»."
    )


def apply_order_admin_action(order, *, action, **payload):
    if action == ACTION_CANCEL:
        return cancel_order_by_admin(order, payload.get("cancellation_reason", ""))
    if action == ACTION_MARK_PAID:
        return mark_order_paid(order, payload.get("payment_method", ""))
    if action == ACTION_SET_STATUS:
        return set_order_status(
            order,
            payload.get("status", ""),
            cancellation_reason=payload.get("cancellation_reason", ""),
        )
    return False, "Άγνωστη ενέργεια."
