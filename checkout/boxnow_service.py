"""Post-checkout Box Now shipment registration."""
import logging

from checkout.boxnow_client import BoxNowAPIError, boxnow_api_enabled, create_delivery_request_for_order
from orders.models import Order

logger = logging.getLogger(__name__)


def schedule_boxnow_delivery(order):
    """
    Create a Box Now delivery request for a new order.

    Failures are logged but do not roll back the order — admin can retry manually.
    """
    if order.delivery_method != Order.DELIVERY_METHOD_BOX_NOW:
        return None
    if not boxnow_api_enabled():
        logger.warning(
            "Box Now API not configured — order %s saved without shipment request.",
            order.order_code,
        )
        return None
    try:
        return create_delivery_request_for_order(order)
    except BoxNowAPIError:
        logger.exception(
            "Box Now delivery request failed for order %s",
            order.order_code,
        )
        return None
