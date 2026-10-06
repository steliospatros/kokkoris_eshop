"""
Stock reservation and release for checkout orders.

Stock is decremented atomically when an order is created at checkout
completion. If another customer buys the last units while items sit in
the cart, checkout is blocked with a clear message.
"""
from collections import defaultdict

from django.db import transaction

from cart.cart import compute_stock_issue
from core import user_text
from products.models import ProductVariant


def expand_cart_variant_quantities(cart_items):
    """
    Map cart lines to total variant units needed.

    Offer packages expand into their component variants × package quantity.
    """
    needed = defaultdict(int)
    owners = defaultdict(list)
    for item in cart_items:
        offer = getattr(item, "offer", None)
        if offer is not None:
            for line in offer.component_lines():
                units = line.quantity * item.quantity
                needed[line.variant_id] += units
                owners[line.variant_id].append(item)
        else:
            variant_id = getattr(item, "product_variant_id", None) or item.product_variant.pk
            needed[variant_id] += item.quantity
            owners[variant_id].append(item)
    return needed, owners


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

    needed, owners = expand_cart_variant_quantities(items)

    with transaction.atomic():
        variants = {
            variant.pk: variant
            for variant in ProductVariant.objects.select_for_update().filter(
                pk__in=list(needed.keys())
            )
        }

        issues = {}
        for variant_id, quantity in needed.items():
            variant = variants.get(variant_id)
            owner = owners[variant_id][0]
            if variant is None:
                issues[owner] = user_text.CART_UNAVAILABLE
                continue
            issue = compute_stock_issue(variant, quantity)
            if issue:
                issues[owner] = issue

        if issues:
            raise InsufficientStockError(issues)

        for variant_id, quantity in needed.items():
            variant = variants[variant_id]
            if variant.availability != ProductVariant.AVAILABILITY_AVAILABLE_NOW:
                continue
            variant.stock -= quantity
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
