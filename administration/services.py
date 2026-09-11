from products.models import Product, ProductVariant


AVAILABILITY_VALUES = {
    ProductVariant.AVAILABILITY_AVAILABLE_NOW,
    ProductVariant.AVAILABILITY_ON_ORDER,
    ProductVariant.AVAILABILITY_OUT_OF_STOCK,
}


def set_variant_inventory(variant, *, stock=None, availability=None):
    """
    Write the new stock count and/or shop availability.

    On-order items belong to supplier stock, so shop quantity stays 0.
    Immediately-available products with 0 stock become temporarily unavailable.
    Restocking without an explicit status puts them back on the shelf.
    """
    update_fields = []
    if stock is not None:
        variant.stock = max(0, int(stock))
        update_fields.append("stock")

    explicit_status = availability in AVAILABILITY_VALUES
    if explicit_status:
        variant.availability = availability
        update_fields.append("availability")

    if variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
        if variant.stock != 0:
            variant.stock = 0
            if "stock" not in update_fields:
                update_fields.append("stock")
    elif variant.stock == 0 and variant.availability == (
        ProductVariant.AVAILABILITY_AVAILABLE_NOW
    ):
        variant.availability = ProductVariant.AVAILABILITY_OUT_OF_STOCK
        if "availability" not in update_fields:
            update_fields.append("availability")
    elif (
        not explicit_status
        and variant.stock > 0
        and variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK
    ):
        variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
        update_fields.append("availability")

    if update_fields:
        variant.save(update_fields=update_fields)
    return variant


def adjust_variant_stock(variant, delta):
    """Add or remove stock units; keep availability in sync for shop stock."""
    if not delta:
        return variant
    return set_variant_inventory(variant, stock=max(0, variant.stock + delta))


def set_product_paused(product, paused):
    """Hide or restore a product on the storefront (all variants)."""
    if product.is_active == (not paused):
        return product
    product.is_active = not paused
    product.save(update_fields=["is_active"])
    return product
