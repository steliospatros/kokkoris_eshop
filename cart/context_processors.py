from cart.cart import get_cart


def cart_state(request):
    """Expose cart item count for the nav badge."""
    cart = get_cart(request)
    return {"cart_total_items": cart.total_items}
