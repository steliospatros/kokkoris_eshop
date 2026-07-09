import os

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand

from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    """
    Sync the Google SocialApp record from .env into the database.

    Idempotent: safe to run on every deploy or after updating credentials.

    Usage:
        python manage.py setup_oauth
    """

    help = "Sync Google OAuth SocialApp from GOOGLE_OAUTH_* env vars to Site id=1."

    def handle(self, *args, **options):
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()

        if not client_id or not secret:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping: set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env first."
                )
            )
            return

        site = Site.objects.get(pk=1)
        app, created = SocialApp.objects.update_or_create(
            provider="google",
            defaults={
                "name": "Google",
                "client_id": client_id,
                "secret": secret,
            },
        )
        app.sites.set([site])

        if created:
            self.stdout.write(self.style.SUCCESS("Created Google SocialApp for Site id=1."))
        else:
            self.stdout.write(self.style.SUCCESS("Updated Google SocialApp for Site id=1."))
