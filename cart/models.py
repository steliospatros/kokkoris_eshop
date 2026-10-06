from django.conf import settings
from django.db import models
from django.db.models import Q

from products.models import Offer, ProductVariant


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
    A cart line: either one product variant or one offer package.
    Price is read live from the variant or offer (never frozen here).
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
        null=True,
        blank=True,
        help_text="Package size line (null when this row is an offer package).",
    )
    offer = models.ForeignKey(
        Offer,
        on_delete=models.CASCADE,
        related_name="cart_items",
        null=True,
        blank=True,
        help_text="Package offer line (null for normal variant lines).",
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(offer__isnull=False, product_variant__isnull=True)
                    | Q(offer__isnull=True, product_variant__isnull=False)
                ),
                name="cartitem_variant_xor_offer",
            ),
            models.UniqueConstraint(
                fields=["cart", "product_variant"],
                condition=Q(product_variant__isnull=False),
                name="unique_cart_variant",
            ),
            models.UniqueConstraint(
                fields=["cart", "offer"],
                condition=Q(offer__isnull=False),
                name="unique_cart_offer",
            ),
        ]

    def __str__(self):
        if self.offer_id:
            return f"{self.quantity}x offer#{self.offer_id} (Cart #{self.cart_id})"
        return f"{self.quantity}x {self.product_variant} (Cart #{self.cart_id})"

    @property
    def subtotal(self):
        """Live price x quantity - recalculated every time, never frozen."""
        if self.offer_id:
            return self.quantity * self.offer.selling_price
        return self.quantity * self.product_variant.selling_price

    def get_stock_issue(self):
        """Delegates to the shared availability/stock rules in cart/cart.py."""
        from .cart import compute_offer_stock_issue, compute_stock_issue

        if self.offer_id:
            return compute_offer_stock_issue(self.offer, self.quantity)
        return compute_stock_issue(self.product_variant, self.quantity)
