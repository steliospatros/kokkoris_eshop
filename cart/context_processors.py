from cart.cart import get_cart
from products.shipping_promo import build_free_shipping_promo


def cart_state(request):
    """Expose cart item count and free-shipping promo for templates."""
    cart = get_cart(request)
    promo = build_free_shipping_promo(cart.total) if cart.total_items else None
    return {
        "cart_total_items": cart.total_items,
        "free_shipping_promo": promo,
    }
