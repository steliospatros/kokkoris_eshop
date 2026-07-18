from products.models import Product, ProductVariant


def adjust_variant_stock(variant, delta):
    """Add or remove stock units; keep availability in sync for shop stock."""
    if not delta:
        return variant

    variant.stock = max(0, variant.stock + delta)
    update_fields = ["stock"]

    if variant.availability == ProductVariant.AVAILABILITY_AVAILABLE_NOW and variant.stock == 0:
        variant.availability = ProductVariant.AVAILABILITY_OUT_OF_STOCK
        update_fields.append("availability")
    elif (
        variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK
        and variant.stock > 0
    ):
        variant.availability = ProductVariant.AVAILABILITY_AVAILABLE_NOW
        update_fields.append("availability")

    variant.save(update_fields=update_fields)
    return variant


def set_product_paused(product, paused):
    """Hide or restore a product on the storefront (all variants)."""
    if product.is_active == (not paused):
        return product
    product.is_active = not paused
    product.save(update_fields=["is_active"])
    return product
