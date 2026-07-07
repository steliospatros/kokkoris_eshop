from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from products.models import ProductVariant

from .cart import CartError, DBCart, SessionCart


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    """
    If the visitor had items in their guest (session-based) cart before
    logging in, move those items into their persistent database cart and
    then empty the guest cart.

    This works correctly without any extra plumbing because Django's
    login() rotates the session key (cycle_key(), for session-fixation
    protection) but PRESERVES the in-memory session data while doing so -
    so request.session["cart"] is still the guest's cart data at the
    point this signal fires, even though the underlying session key has
    already changed.
    """
    guest_data = request.session.get(SessionCart.SESSION_KEY)
    if not guest_data:
        return

    db_cart = DBCart(user)
    for variant_id_str, quantity in guest_data.items():
        try:
            variant = ProductVariant.objects.get(pk=int(variant_id_str))
        except (ProductVariant.DoesNotExist, ValueError):
            continue
        try:
            db_cart.add_item(variant, quantity=quantity)
        except CartError:
            # Not enough stock to honor the merged quantity - skip this
            # line rather than failing the whole login.
            continue

    # Reset the guest cart so the browser's "default" cart is empty again.
    request.session[SessionCart.SESSION_KEY] = {}
    request.session.modified = True
