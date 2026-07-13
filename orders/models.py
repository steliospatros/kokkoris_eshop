from django.conf import settings
from django.db import models

from products.models import ProductVariant


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
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FAILED, "Failed"),
    ]
    # Statuses from which a customer may still self-cancel (before staff
    # have to get involved, e.g. for refunds on an already-paid order).
    CANCELLABLE_STATUSES = (STATUS_NEW, STATUS_PENDING)

    DELIVERY_METHOD_COMPANY = "company_delivery"
    DELIVERY_METHOD_COURIER = "courier"
    DELIVERY_METHOD_CHOICES = [
        (DELIVERY_METHOD_COMPANY, "Free delivery by company staff"),
        (DELIVERY_METHOD_COURIER, "Courier"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        help_text="The customer who placed this order."
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
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
        help_text="Where this order currently stands in the payment/delivery lifecycle."
    )

    # --- Cost breakdown. cart_cost is just the products; courier_fee is the
    # (currently always 0, see checkout.delivery.calculate_courier_fee)
    # shipping surcharge; total_cost is what the customer actually pays. ---
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
                   "here. 0 if delivered for free by company staff. "
                   "Currently always 0 (placeholder) - real per-courier "
                   "pricing (ACS / ELTA Courier / Geniki Taxydromiki) will be "
                   "plugged into that single function in a later step, with "
                   "no changes needed elsewhere."
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
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    delivery_notes = models.TextField(blank=True, default="")
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
        return f"Order #{self.pk} - {self.user.email} ({self.get_status_display()})"

    def can_be_cancelled_by_customer(self):
        """
        Customers may only self-cancel while the order is still 'new' or
        'pending' - i.e. before it has actually been paid/shipped. Once it
        reaches 'paid' or beyond, cancellation must go through staff (e.g.
        to handle a refund), not this self-service action.
        """
        return self.status in self.CANCELLABLE_STATUSES


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
        return f"{self.quantity}x {self.product_variant} (Order #{self.order_id})"

    @property
    def line_total(self):
        """Convenience property: quantity * frozen unit price."""
        return self.quantity * self.price_at_purchase
