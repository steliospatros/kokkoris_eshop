import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from cart.cart import CartError, get_cart
from cart.presentation import build_cart_summary
from core import user_text
from core.http import json_error, json_safe
from products.models import Offer, ProductVariant


def _json_or_post(request):
    if request.content_type == "application/json":
        try:
            return json.loads(request.body.decode("utf-8"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return request.POST


def _parse_int(payload, *keys):
    for key in keys:
        raw = payload.get(key)
        if raw in (None, ""):
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None
    return None


def _cart_payload(cart):
    quantities = {}
    offer_quantities = {}
    for item in cart.items:
        if getattr(item, "offer_id", None) or getattr(item, "offer", None):
            offer = getattr(item, "offer", None)
            oid = getattr(item, "offer_id", None) or (offer.pk if offer else None)
            if oid:
                offer_quantities[oid] = item.quantity
        elif item.product_variant_id:
            quantities[item.product_variant_id] = item.quantity
    return {
        "ok": True,
        "total_items": cart.total_items,
        "quantities": quantities,
        "offer_quantities": offer_quantities,
    }


@require_GET
@json_safe
def status(request):
    """Return current cart totals and per-variant quantities for the catalog UI."""
    cart = get_cart(request)
    return JsonResponse(_cart_payload(cart))


@require_GET
@json_safe
def preview(request):
    """Return cart lines with product details for the nav mini-panel and cart page."""
    cart = get_cart(request)
    payload = build_cart_summary(cart)
    payload["ok"] = True
    return JsonResponse(payload)


@require_POST
@json_safe
def clear(request):
    """Remove every line from the cart."""
    cart = get_cart(request)
    cart.clear()
    payload = _cart_payload(cart)
    return JsonResponse(payload)


@require_POST
@json_safe
def add(request):
    """Add one unit of a variant or one offer package."""
    payload = _json_or_post(request)
    offer_id = _parse_int(payload, "offer_id")
    variant_id = _parse_int(payload, "variant_id")
    cart = get_cart(request)

    if offer_id:
        try:
            offer = Offer.objects.prefetch_related("items__variant__product").get(pk=offer_id)
        except Offer.DoesNotExist:
            return json_error(user_text.CART_PRODUCT_UNKNOWN, status=404)
        try:
            cart.add_offer(offer, quantity=1)
        except CartError as exc:
            return json_error(str(exc))
        result = _cart_payload(cart)
        result["offer_id"] = offer_id
        result["quantity"] = result["offer_quantities"].get(offer_id, 1)
        return JsonResponse(result)

    if not variant_id:
        return json_error(user_text.CART_PRODUCT_UNKNOWN)

    try:
        variant = ProductVariant.objects.select_related("product").get(pk=variant_id)
    except ProductVariant.DoesNotExist:
        return json_error(user_text.CART_SIZE_GONE, status=404)

    try:
        cart.add_item(variant, quantity=1)
    except CartError as exc:
        return json_error(str(exc))

    result = _cart_payload(cart)
    result["variant_id"] = variant_id
    result["quantity"] = result["quantities"].get(variant_id, 1)
    return JsonResponse(result)


@require_POST
@json_safe
def update(request):
    """Set exact quantity for a variant or offer (0 removes the line)."""
    payload = _json_or_post(request)
    offer_id = _parse_int(payload, "offer_id")
    variant_id = _parse_int(payload, "variant_id")
    quantity = _parse_int(payload, "quantity")
    if quantity is None:
        quantity = 0
    if quantity < 0:
        return json_error(user_text.CART_QTY_INVALID)

    cart = get_cart(request)

    if offer_id:
        try:
            offer = Offer.objects.prefetch_related("items__variant__product").get(pk=offer_id)
        except Offer.DoesNotExist:
            return json_error(user_text.CART_PRODUCT_UNKNOWN, status=404)
        try:
            if quantity == 0:
                cart.remove_offer(offer)
            else:
                cart.update_offer(offer, new_quantity=quantity)
        except CartError as exc:
            return json_error(str(exc))
        result = _cart_payload(cart)
        result["offer_id"] = offer_id
        result["quantity"] = quantity
        return JsonResponse(result)

    if not variant_id:
        return json_error(user_text.CART_PRODUCT_UNKNOWN)

    try:
        variant = ProductVariant.objects.get(pk=variant_id)
    except ProductVariant.DoesNotExist:
        return json_error(user_text.CART_SIZE_GONE, status=404)

    try:
        if quantity == 0:
            cart.remove_item(variant)
        else:
            cart.update_item(variant, new_quantity=quantity)
    except CartError as exc:
        return json_error(str(exc))

    result = _cart_payload(cart)
    result["variant_id"] = variant_id
    result["quantity"] = quantity
    return JsonResponse(result)
