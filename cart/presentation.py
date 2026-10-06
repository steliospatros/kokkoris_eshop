"""Shared cart line formatting for pages, previews, and APIs."""
from django.urls import reverse

from cart.cart import DBCart
from products.catalog import format_decimal_greek, get_display_title, get_stock_display
from products.offers import offer_regular_total


def _offer_component_payload(line, *, package_qty):
    product = line.variant.product
    per_package = line.quantity
    total_units = per_package * package_qty
    return {
        "title": get_display_title(product, line.variant),
        "image_url": product.image.url if product.image else None,
        "detail_url": (
            reverse("products:detail", kwargs={"slug": product.slug})
            if product.slug
            else ""
        ),
        "per_package": per_package,
        "quantity": total_units,
        "status_label": "Μέρος προσφοράς",
    }


def build_cart_line(item):
    offer = getattr(item, "offer", None)
    if offer is not None:
        components = [
            _offer_component_payload(line, package_qty=item.quantity)
            for line in offer.component_lines()
        ]
        images = [c["image_url"] for c in components if c["image_url"]]
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
            "components": components,
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
            "locked_components": True,
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
        "components": [],
        "quantity": item.quantity,
        "unit_price": variant.selling_price,
        "unit_price_display": format_decimal_greek(variant.selling_price),
        "regular_price_display": "",
        "discount_percent": 0,
        "subtotal": item.subtotal,
        "subtotal_display": format_decimal_greek(item.subtotal),
        "max_quantity": stock["max_quantity"],
        "can_add": stock["can_add"],
        "locked_components": False,
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
