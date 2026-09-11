import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import send_order_status_email
from .models import Order
from .stock import release_stock_for_order

logger = logging.getLogger(__name__)

_EQUIVALENT_STATUSES = {
    Order.STATUS_NEW: Order.STATUS_NEW,
    Order.STATUS_PENDING: Order.STATUS_NEW,
    Order.STATUS_PAID: Order.STATUS_NEW,
    Order.STATUS_FAILED: Order.STATUS_CANCELLED,
    Order.STATUS_CANCELLED: Order.STATUS_CANCELLED,
    Order.STATUS_DELIVERED: Order.STATUS_DELIVERED,
    Order.STATUS_CANCELLATION_REQUESTED: Order.STATUS_CANCELLATION_REQUESTED,
}


def _customer_status_key(status):
    return _EQUIVALENT_STATUSES.get(status, status)


@receiver(pre_save, sender=Order)
def _remember_previous_order_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return
    instance._previous_status = (
        Order.objects.filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender=Order)
def _email_customer_on_order_status_change(sender, instance, created, **kwargs):
    # New-order email is sent from checkout after OrderItems exist.
    if created:
        return
    previous_status = getattr(instance, "_previous_status", None)
    if (
        instance.status == Order.STATUS_CANCELLED
        and previous_status not in (None, Order.STATUS_CANCELLED)
    ):
        try:
            release_stock_for_order(instance)
        except Exception:
            logger.exception("Failed to restore stock for cancelled order %s", instance.pk)

    try:
        if (
            previous_status != instance.status
            and _customer_status_key(previous_status)
            != _customer_status_key(instance.status)
        ):
            send_order_status_email(
                instance,
                previous_status=previous_status,
            )
    except Exception:
        logger.exception("Failed to send order email for order %s", instance.pk)
