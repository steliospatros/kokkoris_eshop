"""Subscribe an email address to the store newsletter."""
from newsletter.models import NewsletterSubscriber


def subscribe_newsletter(*, email: str, user=None) -> bool:
    """
    Add or reactivate a newsletter subscription.

    Returns True when a new subscription was created or reactivated.
    """
    normalized = (email or "").lower().strip()
    if not normalized:
        return False

    subscriber, created = NewsletterSubscriber.objects.get_or_create(
        email=normalized,
        defaults={"user": user},
    )
    if created:
        return True

    updated = False
    if not subscriber.is_active:
        subscriber.resubscribe()
        updated = True
    if user and not subscriber.user_id:
        subscriber.user = user
        subscriber.save(update_fields=["user"])
    return updated
