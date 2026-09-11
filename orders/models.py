from django.conf import settings
from django.db import models

from products.models import ProductVariant


def _default_order_code():
    from .codes import generate_order_code

    return generate_order_code()


class Order(models.Model):
    """
    A customer's order. Holds everything that stays the same for the whole
    order (who placed it, when, how it will be paid, and its total).
    Individual products/quantities live on OrderItem.

    Full checkout logic (cart -> order conversion, Stripe payments, address
    snapshotting, etc.) is built in Part 4. This model only defines the
    data structure so it is ready when we get there.
    """

    PAYMENT_METHOD_CARD = "card"
    PAYMENT_METHOD_COD = "cash_on_delivery"
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CARD, "Card"),
        (PAYMENT_METHOD_COD, "Cash on Delivery"),
    ]

    STATUS_NEW = "new"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CANCELLATION_REQUESTED = "cancel_req"
    # Legacy values collapsed by migration 0013; kept so leftover rows still
    # behave until that migration runs, and so older code can map them.
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_NEW, "Registered"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_CANCELLATION_REQUESTED, "Cancellation requested"),
    ]
    IN_PROGRESS_STATUSES = (STATUS_NEW, STATUS_PENDING, STATUS_PAID)

    # Payment is deliberately kept out of `status`, which tracks fulfillment
    # only. These are the settlement states the customer is told about.
    PAYMENT_STATE_PREPAID = "prepaid"
    PAYMENT_STATE_COLLECTED = "collected"
    PAYMENT_STATE_DUE_ON_DELIVERY = "due_on_delivery"
    PAYMENT_STATE_REFUNDED = "refunded"
    PAYMENT_STATE_NOT_CHARGED = "not_charged"
    SETTLED_PAYMENT_STATES = (PAYMENT_STATE_PREPAID, PAYMENT_STATE_COLLECTED)

    DELIVERY_METHOD_COMPANY = "company_delivery"
    DELIVERY_METHOD_COURIER = "courier"
    DELIVERY_METHOD_BOX_NOW = "box_now"
    DELIVERY_METHOD_CHOICES = [
        (DELIVERY_METHOD_COMPANY, "Free delivery by company staff"),
        (DELIVERY_METHOD_COURIER, "Courier"),
        (DELIVERY_METHOD_BOX_NOW, "Box Now locker"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="The customer who placed this order."
    )
    order_code = models.CharField(
        max_length=16,
        unique=True,
        default=_default_order_code,
        help_text="Public order identifier shown to customers, e.g. KPK4F8A2B1C.",
    )
    order_date = models.DateTimeField(auto_now_add=True)
    special_notes = models.TextField(
        blank=True,
        help_text="Optional special comments/instructions about this order."
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="How the customer will pay for this order."
    )
    collected_payment_method = models.CharField(
        max_length=20,
        blank=True,
        default="",
        choices=[
            ("", "Not collected"),
            (PAYMENT_METHOD_CARD, "Card"),
            (PAYMENT_METHOD_COD, "Cash"),
        ],
        help_text="Cash or card actually collected at delivery. Empty until the courier declares it, or for prepaid Stripe.",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When staff marked this order as delivered.",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        help_text="Fulfillment only: registered, delivered, cancellation requested, or cancelled. Payment is tracked separately."
    )

    # --- Cost breakdown. cart_cost is just the products; courier_fee is the
    # shipping surcharge from checkout.delivery.calculate_courier_fee
    # (flat courier fee or Box Now locker pricing); total_cost is what the
    # customer actually pays. ---
    cart_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Sum of all order items at the time of purchase, excluding "
                   "any delivery/courier fee. Stored directly so it never "
                   "changes even if product prices change later."
    )
    courier_fee = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Courier delivery fee, computed via checkout.delivery."
                   "calculate_courier_fee() at checkout time and snapshotted "
                   "here. 0 if delivered for free by company staff or when "
                   "the cart qualifies for free shipping. Door courier uses "
                   "a flat fee (COURIER_FLAT_FEE) until a carrier is chosen."
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="cart_cost + courier_fee - the final amount the customer actually pays."
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe PaymentIntent ID for card payments (pi_...). Empty for cash on delivery.",
    )
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Stripe Refund ID (re_...) after admin processes a card refund.",
    )
    cancellation_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the customer submitted a cancellation/refund request.",
    )
    cancellation_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason written by staff when cancelling. Shown to the customer.",
    )
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_METHOD_CHOICES,
        help_text="Whether this order is delivered for free by company staff or via courier."
    )

    # --- Delivery details, snapshotted from the customer's profile at the
    # moment of purchase (same idea as price_at_purchase on OrderItem), so
    # historical orders stay accurate even if the customer later edits their
    # profile address. ---
    delivery_phone_number = models.CharField(max_length=20)
    delivery_city = models.CharField(max_length=100)
    delivery_address = models.CharField(max_length=255)
    delivery_postal_code = models.CharField(max_length=10)
    delivery_floor = models.CharField(max_length=20, blank=True, default="")
    delivery_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    delivery_notes = models.TextField(blank=True, default="")
    boxnow_locker_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Box Now APM locationId selected at checkout.",
    )
    boxnow_locker_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Display name of the selected Box Now locker.",
    )
    boxnow_locker_address = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Street address of the selected Box Now locker.",
    )
    boxnow_locker_postal_code = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="Postal code of the selected Box Now locker.",
    )
    boxnow_delivery_request_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Box Now delivery-request id returned by the Partner API.",
    )
    boxnow_parcel_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Box Now parcel/voucher id for label printing.",
    )
    boxnow_parcel_state = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Latest BOX NOW parcelState from the Partner API / webhook.",
    )
    boxnow_last_event = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Latest BOX NOW webhook event (use this, not parcelState, for customer copy).",
    )
    boxnow_last_event_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last applied BOX NOW webhook event.",
    )
    boxnow_parcel_pin = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Pickup PIN from BOX NOW webhooks, when provided.",
    )
    preferred_delivery_time = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Free text, e.g. 'Τρίτη απόγευμα 5-7'. No real appointment "
                   "scheduling system yet."
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-order_date"]

    def __str__(self):
        return f"Order #{self.order_code} - {self.user.email} ({self.get_status_display()})"

    @property
    def public_code_display(self):
        """Customer-facing order code with hash prefix."""
        return f"#{self.order_code}"

    def save(self, *args, **kwargs):
        if not self.order_code:
            from .codes import assign_unique_order_code

            self.order_code = assign_unique_order_code(type(self))
        super().save(*args, **kwargs)

    def is_in_progress(self):
        """Not yet delivered or cancelled — still being prepared/shipped."""
        return self.status in self.IN_PROGRESS_STATUSES

    def can_be_cancelled_by_customer(self):
        """Immediate cancel for unpaid orders (cash on delivery)."""
        return self.is_in_progress() and not self.is_prepaid_card()

    def can_request_cancellation(self):
        """Prepaid card orders: customer submits a refund request for admin review."""
        return self.is_in_progress() and self.is_prepaid_card()

    def can_customer_initiate_cancel(self):
        return self.can_be_cancelled_by_customer() or self.can_request_cancellation()

    def is_refund_pending(self):
        return self.status == self.STATUS_CANCELLATION_REQUESTED

    def is_prepaid_card(self):
        """Paid online with Stripe — money is already received, no door collection."""
        return (
            self.payment_method == self.PAYMENT_METHOD_CARD
            and bool(self.stripe_payment_intent_id)
            and not self.stripe_refund_id
        )

    def payment_is_locked(self):
        """
        Stripe captured the money, so staff can neither re-declare the payment
        nor clear it — not even by undoing a delivery or after a refund.

        Keyed on the PaymentIntent alone, not on payment_method: only online
        card checkout ever stores one, and the flag must still hold if the
        method field was overwritten by hand.
        """
        return bool(self.stripe_payment_intent_id)

    def payment_state(self):
        """
        Whether the money has actually arrived — separate from `status`, which
        only says where the parcel is.

        Checked most-certain-first: a refund and a Stripe capture are facts
        about money that outrank anything the fulfillment flow says, so an
        undelivered card order still reads as paid.
        """
        if self.stripe_refund_id:
            return self.PAYMENT_STATE_REFUNDED
        if self.stripe_payment_intent_id:
            return self.PAYMENT_STATE_PREPAID
        if self.status in (self.STATUS_CANCELLED, self.STATUS_FAILED):
            return self.PAYMENT_STATE_NOT_CHARGED
        if self.collected_payment_method:
            return self.PAYMENT_STATE_COLLECTED
        return self.PAYMENT_STATE_DUE_ON_DELIVERY

    def payment_is_settled(self):
        """True once the order has been paid for, by card online or at the door."""
        return self.payment_state() in self.SETTLED_PAYMENT_STATES

    def needs_collection_declaration(self):
        """Staff must say cash vs card only for door collections, not BOX NOW."""
        if self.delivery_method == self.DELIVERY_METHOD_BOX_NOW:
            return False
        return not self.is_prepaid_card()


class OrderItem(models.Model):
    """
    A single line of an order: one product variant and the quantity
    ordered. The price is 'frozen' at the moment of purchase so that
    historical orders remain accurate even if the product's price changes
    afterwards.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The order this line belongs to."
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="The exact package size/product ordered."
    )
    quantity = models.PositiveIntegerField()
    price_at_purchase = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Snapshot of the variant's price at the moment of purchase."
    )

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product_variant} (Order #{self.order.order_code})"

    @property
    def line_total(self):
        """Convenience property: quantity * frozen unit price."""
        return self.quantity * self.price_at_purchase
