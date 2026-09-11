import logging

from wishlist.wishlist import get_wishlist

logger = logging.getLogger("kokkoris")


def wishlist_state(request):
    if not hasattr(request, "user") or not hasattr(request, "session"):
        return {"wishlist_total_items": 0}
    try:
        wishlist = get_wishlist(request)
        return {"wishlist_total_items": wishlist.count()}
    except Exception:
        logger.exception("wishlist_state failed")
        return {"wishlist_total_items": 0}
