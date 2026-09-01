"""Test Box Now Partner API connectivity."""
from django.conf import settings
from django.core.management.base import BaseCommand

from checkout.boxnow_client import BoxNowAPIError, boxnow_api_enabled, list_destinations


class Command(BaseCommand):
    help = "Verify Box Now OAuth credentials and list nearby lockers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--latlng",
            default="37.9755,23.7348",
            help="GPS coordinates for destination search (default: Athens center).",
        )

    def handle(self, *args, **options):
        if not settings.BOXNOW_PARTNER_ID:
            self.stderr.write(self.style.WARNING("BOXNOW_PARTNER_ID is not set (widget disabled)."))

        if not boxnow_api_enabled():
            self.stderr.write(
                self.style.ERROR(
                    "Box Now API is not fully configured. Set BOXNOW_OAUTH_CLIENT_ID, "
                    "BOXNOW_OAUTH_CLIENT_SECRET, BOXNOW_API_URL and BOXNOW_ORIGIN_LOCATION_ID."
                )
            )
            return

        self.stdout.write(f"API URL: {settings.BOXNOW_API_URL}")
        self.stdout.write(f"Location API: {settings.BOXNOW_LOCATION_API_URL}")
        self.stdout.write(f"Origin locationId: {settings.BOXNOW_ORIGIN_LOCATION_ID}")

        try:
            destinations = list_destinations(latlng=options["latlng"], radius=5000)
        except BoxNowAPIError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(self.style.SUCCESS(f"OAuth OK — {len(destinations)} locker(s) near {options['latlng']}."))
        for dest in destinations[:5]:
            self.stdout.write(
                f"  - [{dest.get('id')}] {dest.get('title') or dest.get('name')} "
                f"({dest.get('addressLine1')}, {dest.get('postalCode')})"
            )
