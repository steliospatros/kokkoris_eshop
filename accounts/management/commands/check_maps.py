import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify Google Maps API key and show Console setup checklist."

    def handle(self, *args, **options):
        key = (settings.GOOGLE_MAPS_API_KEY or "").strip()
        self.stdout.write(self.style.HTTP_INFO("=== Google Maps checklist ===\n"))

        if not key:
            self.stdout.write(
                self.style.ERROR("✗ GOOGLE_MAPS_API_KEY is empty — add it to .env and restart runserver.")
            )
            return

        self.stdout.write(self.style.SUCCESS(f"✓ GOOGLE_MAPS_API_KEY is set ({len(key)} chars)\n"))

        url = (
            "https://maps.googleapis.com/maps/api/geocode/json?"
            + urllib.parse.urlencode({"address": "Athens, Greece", "key": key})
        )
        try:
            with urllib.request.urlopen(url, timeout=15) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            self.stdout.write(self.style.ERROR(f"✗ HTTP error from Google: {exc.code} {exc.reason}"))
            return
        except urllib.error.URLError as exc:
            self.stdout.write(self.style.ERROR(f"✗ Network error: {exc.reason}"))
            return

        status = payload.get("status")
        error_message = payload.get("error_message") or ""

        if status == "OK":
            self.stdout.write(self.style.SUCCESS("✓ Geocoding API responded OK (key works for server-side calls)\n"))
        elif status == "REQUEST_DENIED" and "referer" in error_message.lower():
            self.stdout.write(
                self.style.WARNING(
                    "○ Geocoding API server test: REQUEST_DENIED (expected for browser-only keys)\n"
                    "  Keys restricted to HTTP referrers cannot be used from the server.\n"
                    "  Reverse geocoding on the site runs in the browser — that is fine.\n"
                )
            )
            self.stdout.write(
                self.style.HTTP_INFO(
                    "If the map shows «This page didn't load Google Maps correctly», fix in Console:\n"
                )
            )
        else:
            self.stdout.write(self.style.ERROR(f"✗ Geocoding API status: {status}"))
            if error_message:
                self.stdout.write(self.style.ERROR(f"  {error_message}\n"))

        self.stdout.write(
            "In Google Cloud Console (same project as the API key):\n"
            "  1. Enable billing on the project (required — maps will not load without it)\n"
            "  2. Enable APIs: Maps JavaScript API, Places API, Geocoding API\n"
            "  3. Credentials → your API key → Application restrictions:\n"
            "     Choose «HTTP referrers (websites)» and add BOTH:\n"
            "       http://127.0.0.1:8000/*\n"
            "       http://localhost:8000/*\n"
            "     Open the site with the SAME host you allowed (127.0.0.1 vs localhost).\n"
            "  4. API restrictions: allow Maps JavaScript API, Places API, Geocoding API\n"
            "  5. Wait ~1 minute, hard-refresh the page (Ctrl+Shift+R), restart runserver if .env changed\n"
        )

        if status == "REQUEST_DENIED" and "referer" in error_message.lower():
            self.stdout.write(
                self.style.SUCCESS(
                    "Key is loaded in Django. Browser failure is almost always missing referrer,\n"
                    "billing off, or Maps JavaScript / Places API not enabled.\n"
                )
            )
