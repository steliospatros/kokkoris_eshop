"""
Stripe refund helpers for paid card orders.

Refunds are triggered manually from the Django admin after a customer
submits a cancellation request — never automatically from the storefront.
"""
from decimal import Decimal

import stripe
from django.conf import settings

from checkout.stripe_service import StripeNotConfiguredError, _configure_stripe
from orders.models import Order


class StripeRefundError(RuntimeError):
    """Raised when a Stripe refund cannot be created."""


def order_requires_stripe_refund(order: Order) -> bool:
    if order.status in (Order.STATUS_CANCELLED, Order.STATUS_FAILED):
        return False
    return (
        order.payment_method == Order.PAYMENT_METHOD_CARD
        and bool(order.stripe_payment_intent_id)
        and not order.stripe_refund_id
    )


def create_stripe_refund_for_order(order: Order):
    """
    Refund the full captured amount for a card order back to the original
    payment method via Stripe.
    """
    if not order.stripe_payment_intent_id:
        raise StripeRefundError("Η παραγγελία δεν έχει Stripe PaymentIntent.")
    if order.stripe_refund_id:
        raise StripeRefundError("Η παραγγελία έχει ήδη επιστροφή χρημάτων.")

    _configure_stripe()
    refund = stripe.Refund.create(
        payment_intent=order.stripe_payment_intent_id,
        metadata={
            "order_id": str(order.pk),
            "order_code": order.order_code,
            "site": "kokkorispetfood.gr",
        },
    )
    if refund.status not in ("succeeded", "pending"):
        raise StripeRefundError(f"Η επιστροφή απέτυχε (status: {refund.status}).")
    return refund


def refund_amount_display(order: Order) -> str:
    return f"{order.total_cost.quantize(Decimal('0.01'))} EUR"
