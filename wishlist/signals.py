from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from products.catalog import get_catalog_queryset

from .models import WishlistItem
from .wishlist import SessionWishlist


@receiver(user_logged_in)
def merge_guest_wishlist_on_login(sender, request, user, **kwargs):
    """Move session wishlist items into the user's persistent wishlist on login."""
    guest_ids = request.session.get(SessionWishlist.SESSION_KEY) or []
    if not guest_ids:
        return

    products = get_catalog_queryset().filter(pk__in=guest_ids)
    for product in products:
        WishlistItem.objects.get_or_create(user=user, product=product)

    request.session[SessionWishlist.SESSION_KEY] = []
    request.session.modified = True
