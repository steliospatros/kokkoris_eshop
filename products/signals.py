from django.db.models.signals import post_save
from django.dispatch import receiver

from products.favourites import ensure_favourite_for_product
from products.models import Product


@receiver(post_save, sender=Product)
def create_favourite_for_new_product(sender, instance, created, **kwargs):
    if created:
        ensure_favourite_for_product(instance)
