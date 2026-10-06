"""
Cart engine: exposes a single get_cart(request) entry point that returns
one of two interchangeable implementations, both sharing the same
interface (add_item / add_offer / remove_item / update_item / total /
total_items / get_stock_issues):

- DBCart:      persistent, database-backed cart for a logged-in user.
- SessionCart: ephemeral cart for a guest. Session keys are
               ``v:<variant_id>`` or ``o:<offer_id>`` (legacy bare ids
               still read as variants).
"""
from core import user_text
from products.models import Offer, ProductVariant

from .models import Cart


class CartError(Exception):
    """Raised when a cart operation cannot be completed (e.g. insufficient stock)."""


def compute_stock_issue(product_variant, quantity):
    if not product_variant.product.is_active:
        return user_text.CART_UNAVAILABLE
    if product_variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
        return user_text.CART_SOLD_OUT
    if product_variant.availability == ProductVariant.AVAILABILITY_ON_ORDER:
        return None
    if product_variant.stock == 0:
        return user_text.CART_SOLD_OUT
    if quantity > product_variant.stock:
        return user_text.stock_limited(product_variant.stock)
    return None


def compute_offer_stock_issue(offer, package_qty):
    if not offer.is_active:
        return user_text.CART_UNAVAILABLE
    for line in offer.component_lines():
        needed = line.quantity * package_qty
        issue = compute_stock_issue(line.variant, needed)
        if issue:
            return issue
    return None


def _reject_invalid_add(product_variant, quantity):
    if quantity < 1:
        raise CartError(user_text.CART_QTY_MIN)
    if not product_variant.product.is_active:
        raise CartError(user_text.CART_UNAVAILABLE)
    if product_variant.availability == ProductVariant.AVAILABILITY_OUT_OF_STOCK:
        raise CartError(user_text.CART_SOLD_OUT)
    if (
        product_variant.availability == ProductVariant.AVAILABILITY_AVAILABLE_NOW
        and product_variant.stock == 0
    ):
        raise CartError(user_text.CART_SOLD_OUT)


def _reject_invalid_offer_add(offer, quantity):
    if quantity < 1:
        raise CartError(user_text.CART_QTY_MIN)
    if not offer.is_active or not offer.component_lines():
        raise CartError(user_text.CART_UNAVAILABLE)


class BaseCart:
    @property
    def items(self):
        raise NotImplementedError

    def add_item(self, product_variant, quantity=1):
        raise NotImplementedError

    def add_offer(self, offer, quantity=1):
        raise NotImplementedError

    def remove_item(self, product_variant):
        raise NotImplementedError

    def remove_offer(self, offer):
        raise NotImplementedError

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        raise NotImplementedError

    def update_offer(self, offer, *, new_quantity):
        raise NotImplementedError

    @property
    def total(self):
        return sum(item.subtotal for item in self.items)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items)

    def get_stock_issues(self):
        issues = {}
        for item in self.items:
            issue = item.get_stock_issue()
            if issue:
                issues[item] = issue
        return issues

    def clear(self):
        raise NotImplementedError


class DBCart(BaseCart):
    def __init__(self, user):
        self.cart, _ = Cart.objects.get_or_create(user=user)

    @property
    def items(self):
        return list(
            self.cart.items.select_related(
                "product_variant__product",
                "offer",
            ).prefetch_related("offer__items__variant__product")
        )

    def add_item(self, product_variant, quantity=1):
        _reject_invalid_add(product_variant, quantity)

        existing = self.cart.items.filter(product_variant=product_variant).first()
        new_quantity = (existing.quantity if existing else 0) + quantity
        self._check_stock(product_variant, new_quantity)

        if existing:
            existing.quantity = new_quantity
            existing.save(update_fields=["quantity"])
            return existing
        return self.cart.items.create(product_variant=product_variant, quantity=new_quantity)

    def add_offer(self, offer, quantity=1):
        _reject_invalid_offer_add(offer, quantity)
        existing = self.cart.items.filter(offer=offer).first()
        new_quantity = (existing.quantity if existing else 0) + quantity
        issue = compute_offer_stock_issue(offer, new_quantity)
        if issue:
            raise CartError(issue)
        if existing:
            existing.quantity = new_quantity
            existing.save(update_fields=["quantity"])
            return existing
        return self.cart.items.create(offer=offer, quantity=new_quantity)

    def remove_item(self, product_variant):
        self.cart.items.filter(product_variant=product_variant).delete()

    def remove_offer(self, offer):
        self.cart.items.filter(offer=offer).delete()

    def clear(self):
        self.cart.items.all().delete()

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        item = self.cart.items.filter(product_variant=product_variant).first()
        if not item:
            raise CartError(user_text.CART_NOT_IN_CART)

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

    def update_offer(self, offer, *, new_quantity):
        item = self.cart.items.filter(offer=offer).first()
        if not item:
            raise CartError(user_text.CART_NOT_IN_CART)
        if new_quantity < 1:
            item.delete()
            return None
        issue = compute_offer_stock_issue(offer, new_quantity)
        if issue:
            raise CartError(issue)
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
        return item

    @staticmethod
    def _check_stock(product_variant, quantity):
        issue = compute_stock_issue(product_variant, quantity)
        if issue:
            raise CartError(issue)


class SessionCartItem:
    def __init__(self, *, product_variant=None, offer=None, quantity=1):
        self.product_variant = product_variant
        self.offer = offer
        self.quantity = quantity

    @property
    def product_variant_id(self):
        return self.product_variant.pk if self.product_variant else None

    @property
    def offer_id(self):
        return self.offer.pk if self.offer else None

    @property
    def subtotal(self):
        if self.offer:
            return self.quantity * self.offer.selling_price
        return self.quantity * self.product_variant.selling_price

    def get_stock_issue(self):
        if self.offer:
            return compute_offer_stock_issue(self.offer, self.quantity)
        return compute_stock_issue(self.product_variant, self.quantity)


class SessionCart(BaseCart):
    SESSION_KEY = "cart"

    def __init__(self, session):
        self.session = session
        self.session.setdefault(self.SESSION_KEY, {})

    @property
    def _data(self):
        return self.session[self.SESSION_KEY]

    @staticmethod
    def _variant_key(variant_id):
        return f"v:{variant_id}"

    @staticmethod
    def _offer_key(offer_id):
        return f"o:{offer_id}"

    def _parse_entries(self):
        variant_ids = []
        offer_ids = []
        for key in self._data:
            if key.startswith("o:"):
                offer_ids.append(int(key[2:]))
            elif key.startswith("v:"):
                variant_ids.append(int(key[2:]))
            else:
                # Legacy bare variant ids
                variant_ids.append(int(key))
        return variant_ids, offer_ids

    @property
    def items(self):
        variant_ids, offer_ids = self._parse_entries()
        variants = {
            v.pk: v
            for v in ProductVariant.objects.filter(pk__in=variant_ids).select_related(
                "product"
            )
        }
        offers = {
            o.pk: o
            for o in Offer.objects.filter(pk__in=offer_ids, is_active=True).prefetch_related(
                "items__variant__product"
            )
        }
        result = []
        for key, quantity in self._data.items():
            if key.startswith("o:"):
                offer = offers.get(int(key[2:]))
                if offer:
                    result.append(SessionCartItem(offer=offer, quantity=quantity))
            else:
                vid = int(key[2:] if key.startswith("v:") else key)
                variant = variants.get(vid)
                if variant:
                    result.append(SessionCartItem(product_variant=variant, quantity=quantity))
        return result

    def add_item(self, product_variant, quantity=1):
        _reject_invalid_add(product_variant, quantity)
        key = self._variant_key(product_variant.pk)
        # migrate legacy key if present
        legacy = str(product_variant.pk)
        if legacy in self._data and key not in self._data:
            self._data[key] = self._data.pop(legacy)
        new_quantity = self._data.get(key, 0) + quantity
        self._check_stock(product_variant, new_quantity)
        self._data[key] = new_quantity
        self._mark_modified()

    def add_offer(self, offer, quantity=1):
        _reject_invalid_offer_add(offer, quantity)
        key = self._offer_key(offer.pk)
        new_quantity = self._data.get(key, 0) + quantity
        issue = compute_offer_stock_issue(offer, new_quantity)
        if issue:
            raise CartError(issue)
        self._data[key] = new_quantity
        self._mark_modified()

    def remove_item(self, product_variant):
        key = self._variant_key(product_variant.pk)
        legacy = str(product_variant.pk)
        changed = False
        if self._data.pop(key, None) is not None:
            changed = True
        if self._data.pop(legacy, None) is not None:
            changed = True
        if changed:
            self._mark_modified()

    def remove_offer(self, offer):
        if self._data.pop(self._offer_key(offer.pk), None) is not None:
            self._mark_modified()

    def update_item(self, product_variant, *, new_quantity=None, new_variant=None):
        key = self._variant_key(product_variant.pk)
        legacy = str(product_variant.pk)
        if key not in self._data and legacy in self._data:
            self._data[key] = self._data.pop(legacy)
        if key not in self._data:
            raise CartError(user_text.CART_NOT_IN_CART)

        target_quantity = new_quantity if new_quantity is not None else self._data[key]

        if new_variant and new_variant != product_variant:
            new_key = self._variant_key(new_variant.pk)
            merged_quantity = self._data.get(new_key, 0) + target_quantity
            self._check_stock(new_variant, merged_quantity)
            del self._data[key]
            self._data[new_key] = merged_quantity
        else:
            self._check_stock(product_variant, target_quantity)
            self._data[key] = target_quantity

        self._mark_modified()

    def update_offer(self, offer, *, new_quantity):
        key = self._offer_key(offer.pk)
        if key not in self._data:
            raise CartError(user_text.CART_NOT_IN_CART)
        if new_quantity < 1:
            del self._data[key]
        else:
            issue = compute_offer_stock_issue(offer, new_quantity)
            if issue:
                raise CartError(issue)
            self._data[key] = new_quantity
        self._mark_modified()

    def clear(self):
        self.session[self.SESSION_KEY] = {}
        self._mark_modified()

    def _mark_modified(self):
        self.session.modified = True

    @staticmethod
    def _check_stock(product_variant, quantity):
        issue = compute_stock_issue(product_variant, quantity)
        if issue:
            raise CartError(issue)


def get_cart(request):
    if request.user.is_authenticated:
        return DBCart(request.user)
    return SessionCart(request.session)
