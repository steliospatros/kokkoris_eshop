"""
Wishlist engine — DB-backed for logged-in users, session-backed for guests.
"""
from products.models import Product

from .models import WishlistItem


class DBWishlist:
    def __init__(self, user):
        self.user = user

    @property
    def product_ids(self):
        return set(
            WishlistItem.objects.filter(user=self.user).values_list("product_id", flat=True)
        )

    def count(self):
        return WishlistItem.objects.filter(user=self.user).count()

    def toggle(self, product):
        item = WishlistItem.objects.filter(user=self.user, product=product).first()
        if item:
            item.delete()
            return False
        WishlistItem.objects.create(user=self.user, product=product)
        return True

    def ordered_product_ids(self):
        return list(
            WishlistItem.objects.filter(user=self.user)
            .order_by("-created_at")
            .values_list("product_id", flat=True)
        )


class SessionWishlist:
    """Ephemeral wishlist stored in the visitor session (same lifetime as guest cart)."""

    SESSION_KEY = "wishlist"

    def __init__(self, session):
        self.session = session
        self.session.setdefault(self.SESSION_KEY, [])

    @property
    def _ids(self):
        return self.session[self.SESSION_KEY]

    @property
    def product_ids(self):
        return {int(product_id) for product_id in self._ids}

    def count(self):
        return len(self._ids)

    def toggle(self, product):
        product_id = str(product.pk)
        if product_id in self._ids:
            self._ids.remove(product_id)
            self._mark_modified()
            return False
        self._ids.append(product_id)
        self._mark_modified()
        return True

    def ordered_product_ids(self):
        return [int(product_id) for product_id in reversed(self._ids)]

    def _mark_modified(self):
        self.session.modified = True


def get_wishlist(request):
    if request.user.is_authenticated:
        return DBWishlist(request.user)
    return SessionWishlist(request.session)
