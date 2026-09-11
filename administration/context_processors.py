import logging

from administration.permissions import (
    user_is_administration_user,
    user_is_courier,
    user_is_shop_admin,
)

logger = logging.getLogger("kokkoris")


def administration_access(request):
    user = getattr(request, "user", None)
    try:
        return {
            "is_administration_user": user_is_administration_user(user) if user else False,
            "is_shop_admin": user_is_shop_admin(user) if user else False,
            "is_courier_user": user_is_courier(user) if user else False,
        }
    except Exception:
        logger.exception("administration_access failed")
        return {
            "is_administration_user": False,
            "is_shop_admin": False,
            "is_courier_user": False,
        }
