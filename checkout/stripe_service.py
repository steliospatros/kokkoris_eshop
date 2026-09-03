"""
Stripe PaymentIntent helpers for Kokkoris checkout (step 3 — card payments).

Business flow:
- Cash on delivery bypasses Stripe entirely.
- Card payments create a PaymentIntent for the final checkout total (products +
  shipping, including COD surcharge when applicable only for COD — card uses base
  shipping fee).
- The client confirms the PaymentIntent via Stripe Payment Element; the server
  verifies success before creating the Order.
"""
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings

from orders.models import Order


class StripeNotConfiguredError(RuntimeError):
    """Raised when Stripe keys are missing from the environment."""


class StripePaymentError(RuntimeError):
    """Raised when a PaymentIntent is missing or not in a payable state."""


def stripe_payments_enabled():
    """True when both Stripe API keys are configured in Django settings."""
    return bool(settings.STRIPE_PUBLISHABLE_KEY and settings.STRIPE_SECRET_KEY)


def _configure_stripe():
    if not stripe_payments_enabled():
        raise StripeNotConfiguredError(
            "Stripe is not configured. Set STRIPE_PUBLISHABLE_KEY and "
            "STRIPE_SECRET_KEY in .env."
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


def decimal_to_stripe_cents(amount: Decimal) -> int:
    """Convert euros to Stripe's smallest currency unit (cents for EUR)."""
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def create_checkout_payment_intent(
    *,
    total_cost: Decimal,
    user,
    checkout_session_key: str,
):
    """
    Create a PaymentIntent for the current checkout total.

    Metadata links the intent back to the authenticated user and checkout
    session so we can validate it on form submit and in webhooks.
    """
    _configure_stripe()
    try:
        return stripe.PaymentIntent.create(
            amount=decimal_to_stripe_cents(total_cost),
            currency=settings.STRIPE_CURRENCY,
            automatic_payment_methods={"enabled": True},
            receipt_email=user.email or None,
            metadata={
                "user_id": str(user.pk),
                "checkout_session_key": checkout_session_key,
                "site": "kokkorispetfood.gr",
            },
        )
    except stripe.StripeError as exc:
        raise StripePaymentError(
            "Δεν ήταν δυνατή η έναρξη της πληρωμής με κάρτα."
        ) from exc


def retrieve_payment_intent(payment_intent_id: str):
    """Fetch a PaymentIntent from Stripe."""
    if not payment_intent_id:
        raise StripePaymentError("Λείπει η πληρωμή με κάρτα.")
    _configure_stripe()
    try:
        return stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.StripeError as exc:
        raise StripePaymentError(
            "Δεν ήταν δυνατή η επαλήθευση της πληρωμής με κάρτα."
        ) from exc


def verify_card_payment_intent(
    payment_intent_id: str,
    *,
    user,
    checkout_session_key: str,
    expected_total: Decimal | None = None,
):
    """
    Ensure the PaymentIntent succeeded and belongs to this user/checkout session.
    Optionally verify the charged amount matches the server-computed total.
    """
    intent = retrieve_payment_intent(payment_intent_id)
    if intent.status != "succeeded":
        raise StripePaymentError("Η πληρωμή με κάρτα δεν ολοκληρώθηκε.")
    metadata = intent.metadata or {}
    if metadata.get("user_id") != str(user.pk):
        raise StripePaymentError("Η πληρωμή δεν αντιστοιχεί στον λογαριασμό σου.")
    if metadata.get("checkout_session_key") != checkout_session_key:
        raise StripePaymentError("Η πληρωμή δεν αντιστοιχεί στο τρέχον checkout.")
    if expected_total is not None:
        if intent.amount != decimal_to_stripe_cents(expected_total):
            raise StripePaymentError("Το ποσό πληρωμής δεν ταιριάζει με την παραγγελία.")
    return intent


def find_order_for_payment_intent(payment_intent_id: str, *, user):
    """Return an existing order for this PaymentIntent (idempotent checkout)."""
    if not payment_intent_id:
        return None
    return Order.objects.filter(
        stripe_payment_intent_id=payment_intent_id,
        user=user,
    ).first()


def card_order_status():
    """Orders paid online are marked paid immediately after Stripe confirms."""
    return Order.STATUS_PAID
