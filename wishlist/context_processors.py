from wishlist.wishlist import get_wishlist


def wishlist_state(request):
    wishlist = get_wishlist(request)
    return {"wishlist_total_items": wishlist.count()}
