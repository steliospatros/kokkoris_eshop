from django.conf import settings
from django.db import models
from django.utils import timezone


class NewsletterSubscriber(models.Model):
    """
    Simple mailing-list entry for future bulk newsletter sends.

    Kept separate from CustomUser so visitors can subscribe without creating
    an account. Use is_active=False when someone unsubscribes.
    """

    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="newsletter_subscriptions",
        help_text="Linked account when the visitor was logged in at signup.",
    )

    class Meta:
        ordering = ["-subscribed_at"]
        verbose_name = "Newsletter subscriber"
        verbose_name_plural = "Newsletter subscribers"

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"{self.email} ({status})"

    def unsubscribe(self):
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save(update_fields=["is_active", "unsubscribed_at"])

    def resubscribe(self):
        self.is_active = True
        self.unsubscribed_at = None
        self.save(update_fields=["is_active", "unsubscribed_at"])
