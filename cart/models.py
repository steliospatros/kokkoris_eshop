from django.conf import settings
from django.db import models

from products.models import ProductVariant


class Cart(models.Model):
    """
    A persistent cart belonging to exactly one registered user.

    Guest (not-logged-in) carts are intentionally NOT stored here at all —
    they live only inside the visitor's browser session (see cart/cart.py:
    SessionCart) and are never written to the database. This keeps the
    database free of abandoned, anonymous cart rows while still giving
    every registered customer a cart that follows them across devices
    and sessions.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        help_text="Each registered user has exactly one persistent cart."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        return f"Cart of {self.user.email}"


class CartItem(models.Model):
    """
    A single line in a registered user's persistent cart: one product
    variant and the quantity requested. Price is intentionally NOT stored
    here - it is always read live from ProductVariant.price (see
    subtotal below), unlike OrderItem.price_at_purchase which freezes it.
    """
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The cart this line belongs to."
    )
    product_variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
        help_text="The exact package size/product placed in the cart."
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        # A given variant can only appear once per cart; quantity changes
        # update this single row instead of creating duplicate lines.
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product_variant"],
                name="unique_cart_variant"
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product_variant} (Cart #{self.cart_id})"

    @property
    def subtotal(self):
        """Live price x quantity - recalculated every time, never frozen."""
        return self.quantity * self.product_variant.price

    def get_stock_issue(self):
        """Delegates to the shared availability/stock rules in cart/cart.py."""
        from .cart import compute_stock_issue
        return compute_stock_issue(self.product_variant, self.quantity)
