"""Store address and Google Maps helpers for the info pages."""
from django.conf import settings
from django.utils.translation import gettext_lazy as _

STORE_ADDRESS_LINE = _("Κρήτης 5, Παλλήνη, Τ.Κ. 15351")
STORE_LATITUDE = 38.00352
STORE_LONGITUDE = 23.88341


def build_store_maps_link() -> str:
    query = "Κρήτης+5,+Παλλήνη+15351"
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def build_store_static_map_url() -> str | None:
    """Static map snapshot for the physical store."""
    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return None
    lat = STORE_LATITUDE
    lng = STORE_LONGITUDE
    return (
        "https://maps.googleapis.com/maps/api/staticmap"
        f"?center={lat},{lng}&zoom=16&size=640x360&scale=2"
        f"&markers=color:0x42746c%7C{lat},{lng}"
        f"&key={api_key}"
    )
