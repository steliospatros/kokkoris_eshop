import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from cart.cart import CartError, get_cart
from cart.presentation import build_cart_summary
from products.models import ProductVariant


def _parse_variant_id(request):
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
            return int(payload.get("variant_id"))
        return int(request.POST.get("variant_id"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _parse_quantity(request, default=1):
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
            raw = payload.get("quantity", default)
        else:
            raw = request.POST.get("quantity", default)
        return int(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _cart_payload(cart):
    quantities = {}
    for item in cart.items:
        quantities[item.product_variant.pk] = item.quantity
    return {
        "ok": True,
        "total_items": cart.total_items,
        "quantities": quantities,
    }


@require_GET
def status(request):
    """Return current cart totals and per-variant quantities for the catalog UI."""
    cart = get_cart(request)
    return JsonResponse(_cart_payload(cart))


@require_GET
def preview(request):
    """Return cart lines with product details for the nav mini-panel and cart page."""
    cart = get_cart(request)
    payload = build_cart_summary(cart)
    payload["ok"] = True
    return JsonResponse(payload)


@require_POST
def clear(request):
    """Remove every line from the cart."""
    cart = get_cart(request)
    cart.clear()
    payload = _cart_payload(cart)
    return JsonResponse(payload)


@require_POST
def add(request):
    """Add one unit of a variant (or merge into existing line)."""
    variant_id = _parse_variant_id(request)
    if not variant_id:
        return JsonResponse({"ok": False, "error": "Μη έγκυρη παραλλαγή."}, status=400)

    try:
        variant = ProductVariant.objects.select_related("product").get(pk=variant_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Η παραλλαγή δεν βρέθηκε."}, status=404)

    cart = get_cart(request)
    try:
        cart.add_item(variant, quantity=1)
    except CartError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    payload = _cart_payload(cart)
    payload["variant_id"] = variant_id
    payload["quantity"] = next(
        (q for vid, q in payload["quantities"].items() if int(vid) == variant_id),
        1,
    )
    return JsonResponse(payload)


@require_POST
def update(request):
    """Set exact quantity for a variant (0 removes the line)."""
    variant_id = _parse_variant_id(request)
    quantity = _parse_quantity(request, default=0)
    if not variant_id:
        return JsonResponse({"ok": False, "error": "Μη έγκυρη παραλλαγή."}, status=400)
    if quantity < 0:
        return JsonResponse({"ok": False, "error": "Μη έγκυρη ποσότητα."}, status=400)

    try:
        variant = ProductVariant.objects.get(pk=variant_id)
    except ProductVariant.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Η παραλλαγή δεν βρέθηκε."}, status=404)

    cart = get_cart(request)
    try:
        if quantity == 0:
            cart.remove_item(variant)
        else:
            cart.update_item(variant, new_quantity=quantity)
    except CartError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    payload = _cart_payload(cart)
    payload["variant_id"] = variant_id
    payload["quantity"] = quantity
    return JsonResponse(payload)
