"""
Catalog presentation helpers — card data for the product grid UI.
"""
from decimal import Decimal

from django.db.models import Count, Prefetch

from .models import Product, ProductVariant


def format_decimal_greek(value, places=2):
    """Format a number with comma as decimal separator (Greek convention)."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        text = f"{value:.{places}f}"
    else:
        text = f"{float(value):.{places}f}"
    return text.replace(".", ",")


def format_weight(weight):
    """Human-readable package size, e.g. 18 kg or 0,085 kg."""
    if weight is None:
        return ""
    weight = Decimal(weight)
    if weight >= 1:
        text = format(weight, "f").rstrip("0").rstrip(".")
    else:
        text = format(weight, ".3f").rstrip("0").rstrip(".")
    return text.replace(".", ",")


def get_default_variant(product):
    """Largest package size — used for card price, SKU, and add-to-cart."""
    variants = list(product.variants.all())
    if not variants:
        return None
    return max(variants, key=lambda v: v.weight)


AVAILABILITY_LABELS = {
    ProductVariant.AVAILABILITY_AVAILABLE_NOW: "Άμεσα διαθέσιμο",
    ProductVariant.AVAILABILITY_ON_ORDER: "Κατόπιν παραγγελίας",
    ProductVariant.AVAILABILITY_OUT_OF_STOCK: "Μη διαθέσιμο",
}

STOCK_STATUS_AVAILABLE = "available"
STOCK_STATUS_LIMITED = "limited"
STOCK_STATUS_OUT = "out"
STOCK_STATUS_ON_ORDER = "on_order"


def get_stock_display(variant):
    """
    Customer-facing stock state for catalog cards and cart limits.

    For immediately-available variants the label/colour/button state
    follows real stock levels.  On-order variants ignore stock; manual
    out-of-stock is always blocked.
    """
    if variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
        return {
            "status": STOCK_STATUS_ON_ORDER,
            "label": AVAILABILITY_LABELS[ProductVariant.AVAILABILITY_ON_ORDER],
            "color_class": "text-kokkoris-blue",
            "can_add": True,
            "max_quantity": None,
            "button_label": "Κατόπιν παραγγελίας",
        }

    if variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
        return {
            "status": STOCK_STATUS_OUT,
            "label": "Έλλειψη",
            "color_class": "text-red-600",
            "can_add": False,
            "max_quantity": 0,
        }

    if variant.stock == 0:
        return {
            "status": STOCK_STATUS_OUT,
            "label": "Έλλειψη",
            "color_class": "text-red-600",
            "can_add": False,
            "max_quantity": 0,
        }

    if variant.stock <= 10:
        return {
            "status": STOCK_STATUS_LIMITED,
            "label": "Περιορισμένη διαθεσιμότητα",
            "color_class": "text-kokkoris-dot-orange",
            "can_add": True,
            "max_quantity": variant.stock,
        }

    return {
        "status": STOCK_STATUS_AVAILABLE,
        "label": AVAILABILITY_LABELS[ProductVariant.AVAILABILITY_AVAILABLE_NOW],
        "color_class": "text-emerald-600",
        "can_add": True,
        "max_quantity": variant.stock,
    }


def get_display_title(product, variant):
    """Computed card title: Brand + product name + package size."""
    if not variant:
        return product.name
    unit = variant.unit_label
    weight_text = format_weight(variant.weight)
    return f"{product.company.name} {product.name} {weight_text} {unit}"


def get_catalog_queryset():
    """Active products with variants prefetched for grid rendering."""
    return (
        Product.objects.filter(is_active=True)
        .select_related("company", "animal_type", "category")
        .prefetch_related(
            Prefetch("variants", queryset=ProductVariant.objects.order_by("weight"))
        )
        .annotate(variant_count=Count("variants"))
        .order_by("company__name", "name")
    )


def build_catalog_card(product, *, cart_qty=0, is_wishlisted=False):
    """Plain dict consumed by product_card.html."""
    variant = get_default_variant(product)
    if not variant:
        return None

    unit_price = variant.unit_price
    count = product.variant_count
    if count == 1:
        sizes_label = "1 ΜΕΓΕΘΟΣ"
    else:
        sizes_label = f"{count} ΜΕΓΕΘΗ"

    stock_display = get_stock_display(variant)

    return {
        "product_id": product.id,
        "variant_id": variant.id,
        "sku": variant.sku or "",
        "title": get_display_title(product, variant),
        "sizes_label": sizes_label,
        "variant_count": count,
        "price": variant.price,
        "price_display": format_decimal_greek(variant.price),
        "unit_price_display": format_decimal_greek(unit_price) if unit_price else "",
        "unit_label": variant.unit_label,
        "availability": variant.availability,
        "stock": variant.stock,
        "stock_status": stock_display["status"],
        "availability_label": stock_display["label"],
        "availability_color_class": stock_display["color_class"],
        "can_add": stock_display["can_add"],
        "max_quantity": stock_display["max_quantity"],
        "is_on_order": stock_display["status"] == STOCK_STATUS_ON_ORDER,
        "button_label": stock_display.get("button_label", "Αγορά"),
        "image_url": product.image.url if product.image else None,
        "cart_qty": cart_qty,
        "is_wishlisted": is_wishlisted,
    }


def build_catalog_cards(products, cart_quantities=None, wishlisted_ids=None):
    """Build card dicts for a queryset/list of products."""
    cart_quantities = cart_quantities or {}
    wishlisted_ids = wishlisted_ids or set()
    cards = []
    for product in products:
        variant = get_default_variant(product)
        if not variant:
            continue
        card = build_catalog_card(
            product,
            cart_qty=cart_quantities.get(variant.id, 0),
            is_wishlisted=product.id in wishlisted_ids,
        )
        if card:
            cards.append(card)
    return cards
