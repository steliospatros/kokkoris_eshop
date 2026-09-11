import logging

from cart.cart import get_cart
from products.shipping_promo import build_free_shipping_promo

logger = logging.getLogger("kokkoris")


def cart_state(request):
    """Expose cart item count and free-shipping promo for templates."""
    if not hasattr(request, "user"):
        return {
            "cart_total_items": 0,
            "free_shipping_promo": None,
        }
    try:
        cart = get_cart(request)
        promo = build_free_shipping_promo(cart.total) if cart.total_items else None
        return {
            "cart_total_items": cart.total_items,
            "free_shipping_promo": promo,
        }
    except Exception:
        logger.exception("cart_state failed")
        return {
            "cart_total_items": 0,
            "free_shipping_promo": None,
        }
