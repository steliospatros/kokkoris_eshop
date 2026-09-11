"""
Stock reservation and release for checkout orders.

Stock is decremented atomically when an order is created at checkout
completion. If another customer buys the last units while items sit in
the cart, checkout is blocked with a clear message.
"""
from django.db import transaction

from cart.cart import compute_stock_issue
from core import user_text
from products.models import ProductVariant


def _cart_item_variant_id(item):
    return getattr(item, "product_variant_id", None) or item.product_variant.pk


class InsufficientStockError(Exception):
    """Raised when cart lines cannot be fulfilled with current stock."""

    def __init__(self, issues):
        self.issues = issues
        super().__init__("Insufficient stock")


def reserve_stock_for_cart(cart):
    """
    Lock variants, re-validate stock, and decrement counts for the cart.

    Only variants with availability ``available_now`` consume stock.
    """
    items = list(cart.items)
    if not items:
        return

    with transaction.atomic():
        variant_ids = [_cart_item_variant_id(item) for item in items]
        variants = {
            variant.pk: variant
            for variant in ProductVariant.objects.select_for_update().filter(
                pk__in=variant_ids
            )
        }

        issues = {}
        for item in items:
            variant_id = _cart_item_variant_id(item)
            variant = variants.get(variant_id)
            if variant is None:
                issues[item] = user_text.CART_UNAVAILABLE
                continue
            issue = compute_stock_issue(variant, item.quantity)
            if issue:
                issues[item] = issue

        if issues:
            raise InsufficientStockError(issues)

        for item in items:
            variant = variants[_cart_item_variant_id(item)]
            if variant.availability != ProductVariant.AVAILABILITY_AVAILABLE_NOW:
                continue
            variant.stock -= item.quantity
            update_fields = ["stock"]
            if variant.stock == 0:
                variant.availability = ProductVariant.AVAILABILITY_OUT_OF_STOCK
                update_fields.append("availability")
            variant.save(update_fields=update_fields)


def release_stock_for_order(order):
    """Return reserved stock when a customer cancels an order."""
    with transaction.atomic():
        for item in order.items.select_related("product_variant"):
            variant = ProductVariant.objects.select_for_update().get(
                pk=item.product_variant_id
            )
            if variant.availability not in (
                ProductVariant.AVAILABILITY_AVAILABLE_NOW,
                ProductVariant.AVAILABILITY_OUT_OF_STOCK,
            ):
                continue
            variant.stock += item.quantity
            update_fields = ["stock"]
            if (
                variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK
                and variant.stock > 0
            ):
                variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
                update_fields.append("availability")
            variant.save(update_fields=update_fields)
