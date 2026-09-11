import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from products.catalog import build_catalog_cards, get_catalog_queryset
from products.favourites import record_wishlist_change
from products.models import Product

from cart.cart import get_cart
from .wishlist import get_wishlist


def _cart_quantities(request):
    cart = get_cart(request)
    return {item.product_variant.pk: item.quantity for item in cart.items}


@require_GET
def status(request):
    wishlist = get_wishlist(request)
    return JsonResponse({"total_items": wishlist.count()})


@require_POST
def toggle(request):
    """Add or remove a product from the current visitor's wishlist."""
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
            product_id = int(payload.get("product_id"))
        else:
            product_id = int(request.POST.get("product_id"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Μη έγκυρο προϊόν."}, status=400)

    try:
        product = get_catalog_queryset().get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Το προϊόν δεν βρέθηκε."}, status=404)

    wishlist = get_wishlist(request)
    wishlisted = wishlist.toggle(product)
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_staff", False):
        record_wishlist_change(product, added=wishlisted)
    return JsonResponse(
        {
            "ok": True,
            "wishlisted": wishlisted,
            "product_id": product_id,
            "total_items": wishlist.count(),
        }
    )


def list_view(request):
    wishlist = get_wishlist(request)
    ordered_ids = wishlist.ordered_product_ids()
    products_by_id = {
        product.pk: product
        for product in get_catalog_queryset().filter(pk__in=ordered_ids)
    }
    products = [products_by_id[product_id] for product_id in ordered_ids if product_id in products_by_id]

    cards = build_catalog_cards(
        products,
        cart_quantities=_cart_quantities(request),
        wishlisted_ids=set(ordered_ids),
    )

    return render(
        request,
        "wishlist/list.html",
        {
            "page_title": "Wishlist",
            "product_cards": cards,
            "product_count": len(cards),
            "user_is_authenticated": request.user.is_authenticated,
        },
    )
