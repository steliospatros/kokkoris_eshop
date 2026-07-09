import os

from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.urls import reverse

from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = "Show Google OAuth setup checklist (redirect URIs, client id, test users)."

    def handle(self, *args, **options):
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        callback_path = reverse("google_callback")

        site = Site.objects.get(pk=1)
        uris = [
            f"http://localhost:8000{callback_path}",
            f"http://127.0.0.1:8000{callback_path}",
        ]
        explicit = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
        if explicit:
            uris.insert(0, explicit)

        self.stdout.write(self.style.HTTP_INFO("=== Google OAuth checklist ===\n"))

        if client_id and secret:
            self.stdout.write(self.style.SUCCESS("✓ GOOGLE_OAUTH_CLIENT_ID and SECRET are set in .env"))
        else:
            self.stdout.write(self.style.ERROR("✗ Missing GOOGLE_OAUTH_CLIENT_ID or SECRET in .env"))

        self.stdout.write(f"\nClient ID (must match Google Console):\n  {client_id or '(empty)'}\n")

        db_app = SocialApp.objects.filter(provider="google").first()
        if db_app:
            match = db_app.client_id == client_id
            status = "matches" if match else "DIFFERS from"
            style = self.style.SUCCESS if match else self.style.WARNING
            self.stdout.write(style(f"DB SocialApp client_id {status} .env\n"))
        else:
            self.stdout.write(self.style.WARNING("No Google SocialApp in DB — run: python manage.py setup_oauth\n"))

        self.stdout.write("Add ALL of these under Credentials → OAuth client → Authorized redirect URIs:\n")
        seen = set()
        for uri in uris:
            if uri in seen:
                continue
            seen.add(uri)
            self.stdout.write(f"  {uri}")

        self.stdout.write(
            "\nOptional JavaScript origins (same host, no path):\n"
            "  http://localhost:8000\n"
            "  http://127.0.0.1:8000\n"
        )

        self.stdout.write(f"Django Site domain: {site.domain}\n")
        self.stdout.write(
            "OAuth consent screen → Test users: add the Gmail you use to sign in.\n"
        )

        try:
            from django.test import RequestFactory

            rf = RequestFactory()
            for host in ("127.0.0.1:8000", "localhost:8000"):
                req = rf.get("/", HTTP_HOST=host)
                apps = get_adapter().list_apps(req, provider="google")
                if not apps:
                    continue
                provider = get_adapter().get_provider(req, provider="google")
                oauth2 = provider.get_oauth2_adapter(req)
                actual = oauth2.get_callback_url(req, apps[0])
                self.stdout.write(f"Redirect sent when browsing http://{host}/ →\n  {actual}\n")
        except Exception as exc:
            self.stdout.write(self.style.WARNING(f"Could not simulate redirect URIs: {exc}\n"))
