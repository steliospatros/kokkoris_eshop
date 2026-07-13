"""Shared cart line formatting for pages, previews, and APIs."""
from cart.cart import DBCart, SessionCartItem
from products.catalog import format_decimal_greek, get_display_title, get_stock_display
from products.models import ProductVariant


def _cart_item_list(cart):
    if isinstance(cart, DBCart):
        return list(
            cart.cart.items.select_related(
                "product_variant__product__company",
            )
        )

    variant_ids = [int(vid) for vid in cart._data]
    if not variant_ids:
        return []
    variants = {
        v.pk: v
        for v in ProductVariant.objects.filter(pk__in=variant_ids).select_related(
            "product__company",
        )
    }
    return [
        SessionCartItem(variants[int(vid)], quantity)
        for vid, quantity in cart._data.items()
        if int(vid) in variants
    ]


def build_cart_line(item):
    variant = item.product_variant
    product = variant.product
    stock = get_stock_display(variant)
    return {
        "variant_id": variant.pk,
        "product_id": product.pk,
        "title": get_display_title(product, variant),
        "image_url": product.image.url if product.image else None,
        "quantity": item.quantity,
        "unit_price": variant.price,
        "unit_price_display": format_decimal_greek(variant.price),
        "subtotal": item.subtotal,
        "subtotal_display": format_decimal_greek(item.subtotal),
        "max_quantity": stock["max_quantity"],
        "can_add": stock["can_add"],
    }


def build_cart_lines(cart):
    return [build_cart_line(item) for item in _cart_item_list(cart)]


def build_cart_summary(cart):
    lines = build_cart_lines(cart)
    total = cart.total
    total_items = cart.total_items
    return {
        "lines": lines,
        "total": total,
        "total_display": format_decimal_greek(total),
        "total_items": total_items,
    }
