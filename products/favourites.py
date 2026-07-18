from collections import Counter

from django.db.models import F

from products.models import Favourite, Product


def ensure_favourite_for_product(product):
    favourite, _ = Favourite.objects.get_or_create(
        product=product,
        defaults={"purchase_count": 0},
    )
    return favourite


def increment_favourite_counts(cart_items):
    """
    Increase purchase_count for each product in a cart checkout.

    ``cart_items`` is an iterable of cart line objects with
    ``product_variant`` and ``quantity`` attributes.
    """
    totals = Counter()
    for item in cart_items:
        totals[item.product_variant.product_id] += item.quantity

    for product_id, quantity in totals.items():
        favourite, created = Favourite.objects.get_or_create(
            product_id=product_id,
            defaults={"purchase_count": 0},
        )
        if created:
            Favourite.objects.filter(pk=favourite.pk).update(
                purchase_count=quantity,
            )
        else:
            Favourite.objects.filter(pk=favourite.pk).update(
                purchase_count=F("purchase_count") + quantity,
            )


def build_favourites_rows():
    """Products ranked by purchase_count (highest first) — admin table rows."""
    favourites = (
        Favourite.objects.select_related(
            "product__company",
            "product__category",
            "product__animal_type",
        )
        .order_by("-purchase_count", "product__name")
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
                "purchase_count": favourite.purchase_count,
                "is_active": product.is_active,
            }
        )
    return rows


def get_favourite_products(*, limit=12, exclude_product_ids=None):
    """Active storefront products ordered by purchase popularity."""
    from products.catalog import get_catalog_queryset

    exclude_product_ids = exclude_product_ids or []
    queryset = get_catalog_queryset().order_by("-purchase_count", "name")
    if exclude_product_ids:
        queryset = queryset.exclude(pk__in=exclude_product_ids)
    return list(queryset[:limit])


def build_favourites_browse_cards(request, *, limit=12, exclude_product_ids=None):
    """Browse-style product cards for the favourites strip."""
    from products.catalog import build_catalog_card, get_default_variant

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
