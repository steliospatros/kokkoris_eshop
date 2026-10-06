"""Shared cart line formatting for pages, previews, and APIs."""
from cart.cart import DBCart
from products.catalog import format_decimal_greek, get_display_title, get_stock_display
from products.offers import offer_regular_total


def build_cart_line(item):
    offer = getattr(item, "offer", None)
    if offer is not None:
        images = []
        for line in offer.component_lines():
            product = line.variant.product
            if product.image:
                images.append(product.image.url)
        stock_ok = item.get_stock_issue() is None
        max_packages = None
        for line in offer.component_lines():
            stock = get_stock_display(line.variant)
            if stock["max_quantity"] is not None:
                packs = stock["max_quantity"] // line.quantity
                max_packages = packs if max_packages is None else min(max_packages, packs)
        regular = offer_regular_total(offer)
        return {
            "kind": "offer",
            "offer_id": offer.pk,
            "variant_id": None,
            "product_id": None,
            "title": offer.title,
            "image_url": images[0] if images else None,
            "image_urls": images,
            "quantity": item.quantity,
            "unit_price": offer.selling_price,
            "unit_price_display": format_decimal_greek(offer.selling_price),
            "regular_price_display": (
                format_decimal_greek(regular) if regular > offer.selling_price else ""
            ),
            "discount_percent": offer.discount_percent,
            "subtotal": item.subtotal,
            "subtotal_display": format_decimal_greek(item.subtotal),
            "max_quantity": max_packages,
            "can_add": stock_ok and (max_packages is None or max_packages > 0),
        }

    variant = item.product_variant
    product = variant.product
    stock = get_stock_display(variant)
    return {
        "kind": "variant",
        "offer_id": None,
        "variant_id": variant.pk,
        "product_id": product.pk,
        "title": get_display_title(product, variant),
        "image_url": product.image.url if product.image else None,
        "image_urls": [],
        "quantity": item.quantity,
        "unit_price": variant.selling_price,
        "unit_price_display": format_decimal_greek(variant.selling_price),
        "regular_price_display": "",
        "discount_percent": 0,
        "subtotal": item.subtotal,
        "subtotal_display": format_decimal_greek(item.subtotal),
        "max_quantity": stock["max_quantity"],
        "can_add": stock["can_add"],
    }


def build_cart_lines(cart):
    if isinstance(cart, DBCart):
        items = list(
            cart.cart.items.select_related(
                "product_variant__product__company",
                "offer",
            ).prefetch_related("offer__items__variant__product")
        )
    else:
        items = cart.items
    return [build_cart_line(item) for item in items]


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
