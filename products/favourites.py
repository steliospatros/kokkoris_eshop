from collections import Counter
import uuid

from django.db import IntegrityError
from django.db.models import F, Value
from django.db.models.functions import Greatest

from products.models import Favourite, FavouriteView, Product

SCORE_SALE = 20
SCORE_WISHLIST = 4
SCORE_VIEW = 1

VIEWER_COOKIE = "fp_viewer"
VIEWER_SESSION_KEY = "favourite_visitor_key"
VIEWER_COOKIE_MAX_AGE = 365 * 24 * 60 * 60


def ensure_favourite_for_product(product):
    favourite, _ = Favourite.objects.get_or_create(
        product=product,
        defaults={
            "score": 0,
            "purchase_count": 0,
            "wishlist_count": 0,
            "view_count": 0,
        },
    )
    return favourite


def _adjust_favourite(product_id, *, score=0, purchases=0, wishlists=0, views=0):
    favourite, _ = Favourite.objects.get_or_create(
        product_id=product_id,
        defaults={
            "score": 0,
            "purchase_count": 0,
            "wishlist_count": 0,
            "view_count": 0,
        },
    )
    Favourite.objects.filter(pk=favourite.pk).update(
        score=Greatest(F("score") + score, Value(0)),
        purchase_count=Greatest(F("purchase_count") + purchases, Value(0)),
        wishlist_count=Greatest(F("wishlist_count") + wishlists, Value(0)),
        view_count=Greatest(F("view_count") + views, Value(0)),
    )


def increment_favourite_counts(cart_items):
    """
    Record completed sales: +1 unit and +20 score per quantity.
    """
    totals = Counter()
    for item in cart_items:
        totals[item.product_variant.product_id] += item.quantity

    for product_id, quantity in totals.items():
        _adjust_favourite(
            product_id,
            score=SCORE_SALE * quantity,
            purchases=quantity,
        )


def record_wishlist_change(product, *, added):
    """+4 when a product is wishlisted, −4 when it is removed."""
    if added:
        _adjust_favourite(product.pk, score=SCORE_WISHLIST, wishlists=1)
    else:
        _adjust_favourite(product.pk, score=-SCORE_WISHLIST, wishlists=-1)


def _visitor_key(request):
    """Stable browser id: long-lived cookie, with session as fallback."""
    key = request.COOKIES.get(VIEWER_COOKIE) or request.session.get(VIEWER_SESSION_KEY)
    if not key:
        key = uuid.uuid4().hex
        request._new_favourite_visitor_key = True
    request.session[VIEWER_SESSION_KEY] = key
    if hasattr(request.session, "modified"):
        request.session.modified = True
    request.favourite_visitor_key = key
    return key


def attach_viewer_cookie(response, request):
    """Keep the visitor key for a year so repeat views do not farm score."""
    key = getattr(request, "favourite_visitor_key", None) or request.session.get(
        VIEWER_SESSION_KEY
    )
    if not key:
        return response
    if getattr(request, "_new_favourite_visitor_key", False) or VIEWER_COOKIE not in request.COOKIES:
        response.set_cookie(
            VIEWER_COOKIE,
            key,
            max_age=VIEWER_COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
    return response


def record_product_view(request, product):
    """
    +1 the first time this visitor (logged-in user or same browser) opens the page.
    Repeat views by the same person never add more points. Staff is ignored.
    """
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_staff", False):
        return False
    session = getattr(request, "session", None)
    if session is None:
        return False

    visitor_key = _visitor_key(request)
    auth_user = user if getattr(user, "is_authenticated", False) else None

    if auth_user and FavouriteView.objects.filter(product=product, user=auth_user).exists():
        return False

    existing = FavouriteView.objects.filter(product=product, visitor_key=visitor_key).first()
    if existing:
        if auth_user and existing.user_id is None:
            existing.user = auth_user
            existing.save(update_fields=["user"])
        return False

    try:
        FavouriteView.objects.create(
            product=product,
            user=auth_user,
            visitor_key=visitor_key,
        )
    except IntegrityError:
        return False

    _adjust_favourite(product.pk, score=SCORE_VIEW, views=1)
    return True


def build_favourites_rows():
    """Products ranked by score — administration table rows."""
    favourites = (
        Favourite.objects.select_related(
            "product__company",
            "product__category",
            "product__animal_type",
        )
        .filter(product__is_active=True)
        .order_by("-score", "-purchase_count", "product__name")
    )

    rows = []
    for rank, favourite in enumerate(favourites, start=1):
        product = favourite.product
        rows.append(
            {
                "rank": rank,
                "product_id": product.pk,
                "product_name": product.name,
                "company_name": product.company.name,
                "category_name": product.category.name,
                "animal_name": product.animal_type.name,
                "score": favourite.score,
                "purchase_count": favourite.purchase_count,
                "wishlist_count": favourite.wishlist_count,
                "view_count": favourite.view_count,
                "is_active": product.is_active,
            }
        )
    return rows


def get_favourite_products(*, limit=12, exclude_product_ids=None, mix_seed=0):
    """Popular products, mixed so the strip is not the same every visit."""
    from products.catalog import get_catalog_queryset, popularity_mix_list

    exclude_product_ids = exclude_product_ids or []
    queryset = get_catalog_queryset()
    if exclude_product_ids:
        queryset = queryset.exclude(pk__in=exclude_product_ids)
    products = list(queryset)
    scored = [product for product in products if getattr(product, "score", 0) > 0]
    pool = scored if len(scored) >= limit else products
    return popularity_mix_list(pool, seed=mix_seed)[:limit]


def build_favourites_browse_cards(request, *, limit=12, exclude_product_ids=None):
    """Browse-style product cards for the favourites strip."""
    from products.catalog import build_catalog_card, catalog_mix_seed, get_default_variant

    cart_quantities = {}
    wishlisted_ids = set()
    if hasattr(request, "session"):
        from cart.cart import get_cart
        from wishlist.wishlist import get_wishlist

        cart_quantities = {
            item.product_variant.pk: item.quantity for item in get_cart(request).items
        }
        wishlisted_ids = get_wishlist(request).product_ids

    cards = []
    for product in get_favourite_products(
        limit=limit,
        exclude_product_ids=exclude_product_ids,
        mix_seed=catalog_mix_seed(request),
    ):
        variant = get_default_variant(product)
        if not variant:
            continue
        card = build_catalog_card(
            product,
            cart_qty=cart_quantities.get(variant.id, 0),
            is_wishlisted=product.id in wishlisted_ids,
        )
        if card:
            cards.append(card)
    return cards
