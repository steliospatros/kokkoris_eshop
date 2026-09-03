"""
Cart engine: exposes a single get_cart(request) entry point that returns
one of two interchangeable implementations, both sharing the same
interface (add_item / remove_item / update_item / total / total_items /
get_stock_issues):

- DBCart:      persistent, database-backed cart for a logged-in user.
               One row per user (see cart.models.Cart), never lost.
- SessionCart: ephemeral cart for a guest (not logged in). Stored entirely
               inside request.session as a plain {variant_id: quantity}
               dict - NEVER written to the database. It disappears
               automatically whenever the session expires.

Views/templates should always go through get_cart(request) and never
instantiate DBCart/SessionCart directly, so they don't need to know or
care which backend is actually in use for a given visitor.
"""
from products.models import ProductVariant

from .models import Cart


class CartError(Exception):
    """Raised when a cart operation cannot be completed (e.g. insufficient stock)."""


def compute_stock_issue(product_variant, quantity):
    """
    Single source of truth for stock/availability rules, shared by both
    CartItem (database cart) and SessionCartItem (guest cart):

    - out_of_stock:   never allowed, regardless of quantity.
    - on_order:       special-ordered from the supplier - unlimited
                       quantity, no stock check at all.
    - available_now:  quantity must not exceed the real ProductVariant.stock.

    Returns a human-readable problem message, or None if the line is fine.
    """
    if product_variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
        return "Το προϊόν δεν είναι πλέον διαθέσιμο."
    if product_variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
        return None
    if product_variant.stock == 0:
        return "Το προϊόν δεν είναι διαθέσιμο (έλλειψη αποθέματος)."
    if quantity > product_variant.stock:
        return f"Μόνο {product_variant.stock} τεμάχια διαθέσιμα."
    return None


class BaseCart:
    """Common interface implemented by DBCart and SessionCart."""

    @property
    def items(self):
        raise NotImplementedError

    def add_item(self, product_variant, quantity=1):
        raise NotImplementedError

    def remove_item(self, product_variant):
        raise NotImplementedError

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        raise NotImplementedError

    @property
    def total(self):
        """Always computed live from current prices - never frozen."""
        return sum(item.subtotal for item in self.items)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items)

    def get_stock_issues(self):
        """
        Returns {item: message} for every line that currently has a stock
        problem. Meant to be called again right before checkout (Part 4),
        in case stock changed after the item was added to the cart.
        """
        issues = {}
        for item in self.items:
            issue = item.get_stock_issue()
            if issue:
                issues[item] = issue
        return issues

    def clear(self):
        """Empties the cart entirely. Used right after an order is created."""
        raise NotImplementedError


class DBCart(BaseCart):
    """Persistent, database-backed cart for a logged-in user."""

    def __init__(self, user):
        self.cart, _ = Cart.objects.get_or_create(user=user)

    @property
    def items(self):
        return list(self.cart.items.select_related("product_variant__product"))

    def add_item(self, product_variant, quantity=1):
        if quantity < 1:
            raise CartError("Η ποσότητα πρέπει να είναι τουλάχιστον 1.")
        if product_variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
            raise CartError("Το προϊόν είναι εξαντλημένο και δεν μπορεί να προστεθεί στο καλάθι.")
        if (
            product_variant.availability == ProductVariant.AVAILABILITY_AVAILABLE_NOW
            and product_variant.stock == 0
        ):
            raise CartError("Το προϊόν δεν είναι διαθέσιμο (έλλειψη αποθέματος).")

        existing = self.cart.items.filter(product_variant=product_variant).first()
        new_quantity = (existing.quantity if existing else 0) + quantity
        self._check_stock(product_variant, new_quantity)

        if existing:
            existing.quantity = new_quantity
            existing.save(update_fields=["quantity"])
            return existing
        return self.cart.items.create(product_variant=product_variant, quantity=new_quantity)

    def remove_item(self, product_variant):
        self.cart.items.filter(product_variant=product_variant).delete()

    def clear(self):
        self.cart.items.all().delete()

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        """
        Updates quantity and/or switches to a different variant (e.g. a
        different package size) in place, without a delete+re-add. If the
        target variant already has its own line, quantities are merged.
        """
        item = self.cart.items.filter(product_variant=product_variant).first()
        if not item:
            raise CartError("Το προϊόν δεν βρίσκεται στο καλάθι.")

        target_quantity = new_quantity if new_quantity is not None else item.quantity

        if new_variant and new_variant != product_variant:
            other = self.cart.items.filter(product_variant=new_variant).first()
            if other:
                merged_quantity = other.quantity + target_quantity
                self._check_stock(new_variant, merged_quantity)
                other.quantity = merged_quantity
                other.save(update_fields=["quantity"])
                item.delete()
                return other

            self._check_stock(new_variant, target_quantity)
            item.product_variant = new_variant
            item.quantity = target_quantity
            item.save(update_fields=["product_variant", "quantity"])
            return item

        self._check_stock(product_variant, target_quantity)
        item.quantity = target_quantity
        item.save(update_fields=["quantity"])
        return item

    @staticmethod
    def _check_stock(product_variant, quantity):
        issue = compute_stock_issue(product_variant, quantity)
        if issue:
            raise CartError(issue)


class SessionCartItem:
    """Lightweight, non-persisted stand-in for CartItem - used only for guests."""

    def __init__(self, product_variant, quantity):
        self.product_variant = product_variant
        self.quantity = quantity

    @property
    def product_variant_id(self):
        return self.product_variant.pk

    @property
    def subtotal(self):
        return self.quantity * self.product_variant.selling_price

    def get_stock_issue(self):
        return compute_stock_issue(self.product_variant, self.quantity)


class SessionCart(BaseCart):
    """
    Ephemeral cart for a guest (not logged in). Stored entirely inside
    request.session as a plain {variant_id_str: quantity} dict. NEVER
    written to the database, and disappears automatically together with
    the session.
    """
    SESSION_KEY = "cart"

    def __init__(self, session):
        self.session = session
        self.session.setdefault(self.SESSION_KEY, {})

    @property
    def _data(self):
        return self.session[self.SESSION_KEY]

    @property
    def items(self):
        variant_ids = [int(vid) for vid in self._data]
        variants = {v.pk: v for v in ProductVariant.objects.filter(pk__in=variant_ids)}
        return [
            SessionCartItem(variants[int(vid)], quantity)
            for vid, quantity in self._data.items()
            if int(vid) in variants
        ]

    def add_item(self, product_variant, quantity=1):
        if quantity < 1:
            raise CartError("Η ποσότητα πρέπει να είναι τουλάχιστον 1.")
        if product_variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
            raise CartError("Το προϊόν είναι εξαντλημένο και δεν μπορεί να προστεθεί στο καλάθι.")
        if (
            product_variant.availability == ProductVariant.AVAILABILITY_AVAILABLE_NOW
            and product_variant.stock == 0
        ):
            raise CartError("Το προϊόν δεν είναι διαθέσιμο (έλλειψη αποθέματος).")

        key = str(product_variant.pk)
        new_quantity = self._data.get(key, 0) + quantity
        self._check_stock(product_variant, new_quantity)
        self._data[key] = new_quantity
        self._mark_modified()

    def remove_item(self, product_variant):
        if self._data.pop(str(product_variant.pk), None) is not None:
            self._mark_modified()

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        key = str(product_variant.pk)
        if key not in self._data:
            raise CartError("Το προϊόν δεν βρίσκεται στο καλάθι.")

        target_quantity = new_quantity if new_quantity is not None else self._data[key]

        if new_variant and new_variant != product_variant:
            new_key = str(new_variant.pk)
            merged_quantity = self._data.get(new_key, 0) + target_quantity
            self._check_stock(new_variant, merged_quantity)
            del self._data[key]
            self._data[new_key] = merged_quantity
        else:
            self._check_stock(product_variant, target_quantity)
            self._data[key] = target_quantity

        self._mark_modified()

    def clear(self):
        """Empties the guest cart. Used right after it is merged on login."""
        self.session[self.SESSION_KEY] = {}
        self._mark_modified()

    def _mark_modified(self):
        # Django does NOT auto-detect mutations of nested dicts inside the
        # session - only direct request.session[key] = ... assignments.
        # Without this, changes made via self._data[...] would silently
        # never be persisted.
        self.session.modified = True

    @staticmethod
    def _check_stock(product_variant, quantity):
        issue = compute_stock_issue(product_variant, quantity)
        if issue:
            raise CartError(issue)


def get_cart(request):
    """
    Single entry point used by views: returns a DBCart for logged-in users
    or a SessionCart for guests, both exposing the exact same interface.
    """
    if request.user.is_authenticated:
        return DBCart(request.user)
    return SessionCart(request.session)
