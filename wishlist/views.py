import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from products.models import Product

from .models import WishlistItem


@login_required
@require_POST
def toggle(request):
    """Add or remove a product from the current user's wishlist."""
    try:
        if request.content_type == "application/json":
            payload = json.loads(request.body.decode("utf-8"))
            product_id = int(payload.get("product_id"))
        else:
            product_id = int(request.POST.get("product_id"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Μη έγκυρο προϊόν."}, status=400)

    try:
        product = Product.objects.get(pk=product_id, is_active=True)
    except Product.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Το προϊόν δεν βρέθηκε."}, status=404)

    item = WishlistItem.objects.filter(user=request.user, product=product).first()
    if item:
        item.delete()
        return JsonResponse({"ok": True, "wishlisted": False, "product_id": product_id})

    WishlistItem.objects.create(user=request.user, product=product)
    return JsonResponse({"ok": True, "wishlisted": True, "product_id": product_id})
