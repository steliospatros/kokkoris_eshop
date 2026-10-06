from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from products.models import Offer, ProductVariant

from .cart import CartError, DBCart, SessionCart


@receiver(user_logged_in)
def merge_guest_cart_on_login(sender, request, user, **kwargs):
    """
    If the visitor had items in their guest (session-based) cart before
    logging in, move those items into their persistent database cart and
    then empty the guest cart.
    """
    guest_data = request.session.get(SessionCart.SESSION_KEY)
    if not guest_data:
        return

    db_cart = DBCart(user)
    for key, quantity in guest_data.items():
        try:
            if str(key).startswith("o:"):
                offer = Offer.objects.prefetch_related("items__variant__product").get(
                    pk=int(str(key)[2:])
                )
                db_cart.add_offer(offer, quantity=quantity)
            else:
                raw = str(key)[2:] if str(key).startswith("v:") else str(key)
                variant = ProductVariant.objects.get(pk=int(raw))
                db_cart.add_item(variant, quantity=quantity)
        except (Offer.DoesNotExist, ProductVariant.DoesNotExist, ValueError, CartError):
            continue

    request.session[SessionCart.SESSION_KEY] = {}
    request.session.modified = True
