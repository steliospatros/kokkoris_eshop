import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone

from .models import NewsletterSubscriber


@admin.action(description="Export selected emails as CSV")
def export_emails_csv(modeladmin, request, queryset):
    """Export active subscribers for use with bulk email tools later."""
    response = HttpResponse(content_type="text/csv")
    filename = f"newsletter_subscribers_{timezone.now():%Y%m%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(["email", "is_active", "subscribed_at", "unsubscribed_at"])
    for subscriber in queryset.order_by("email"):
        writer.writerow([
            subscriber.email,
            subscriber.is_active,
            subscriber.subscribed_at.isoformat(),
            subscriber.unsubscribed_at.isoformat() if subscriber.unsubscribed_at else "",
        ])
    return response


@admin.action(description="Mark selected as unsubscribed")
def mark_unsubscribed(modeladmin, request, queryset):
    now = timezone.now()
    updated = queryset.filter(is_active=True).update(is_active=False, unsubscribed_at=now)
    modeladmin.message_user(request, f"{updated} subscriber(s) marked as unsubscribed.")


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "subscribed_at", "unsubscribed_at", "user")
    list_filter = ("is_active", "subscribed_at")
    search_fields = ("email", "user__email")
    readonly_fields = ("subscribed_at", "unsubscribed_at")
    actions = [export_emails_csv, mark_unsubscribed]
