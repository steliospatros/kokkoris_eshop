import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .emails import send_order_status_email
from .models import Order

logger = logging.getLogger(__name__)


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
    try:
        previous_status = getattr(instance, "_previous_status", None)
        if previous_status != instance.status:
            send_order_status_email(
                instance,
                previous_status=previous_status,
            )
    except Exception:
        logger.exception("Failed to send order email for order %s", instance.pk)
