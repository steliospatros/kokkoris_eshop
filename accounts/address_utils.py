"""Helpers for Greek delivery address fields."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings

from checkout.delivery import is_within_athens_urban_area


@dataclass
class ParsedDeliveryAddress:
    city: str = ""
    area: str = ""
    street: str = ""
    street_number: str = ""
    postal_code: str = ""

    @property
    def address(self) -> str:
        """Legacy single-line address used by checkout snapshots."""
        return self.format_street_line()

    def format_street_line(self) -> str:
        street = (self.street or "").strip()
        number = (self.street_number or "").strip()
        if street and number:
            return f"{street} {number}"
        return street or number

    def as_dict(self) -> dict[str, str]:
        return {
            "city": self.city,
            "area": self.area,
            "street": self.street,
            "street_number": self.street_number,
            "postal_code": self.postal_code,
            "address": self.address,
        }


def normalize_postal_code(postal_code: str) -> str:
    return re.sub(r"\s+", "", (postal_code or "").strip())


def resolve_greek_city(city: str, postal_code: str) -> str:
    """
    Return the customer-facing city label.

    In the Athens urban area (TK 10–18), suburb names from Google map to «Αθήνα»
    instead of the Google locality (suburb name).
    """
    if is_within_athens_urban_area(postal_code):
        return "Αθήνα"
    return (city or "").strip()


def _get_component(components: list[dict[str, Any]], *types: str, short: bool = False) -> str:
    for component in components:
        component_types = component.get("types") or []
        if any(t in component_types for t in types):
            key = "short_name" if short else "long_name"
            return (component.get(key) or "").strip()
    return ""


def parse_google_address_components(components: list[dict[str, Any]]) -> ParsedDeliveryAddress:
    """
    Parse Google Geocoding / Places address_components into structured fields.

    For Athens urban TK (10–18):
      - city → «Αθήνα»
      - area → suburb/locality (e.g. Χαλανδρί)
    """
    postal_code = normalize_postal_code(_get_component(components, "postal_code"))
    locality = _get_component(components, "locality")
    sublocality = _get_component(
        components, "sublocality", "sublocality_level_1", "neighborhood"
    )
    admin3 = _get_component(components, "administrative_area_level_3")
    route = _get_component(components, "route")
    street_number = _get_component(components, "street_number")

    if is_within_athens_urban_area(postal_code):
        city = "Αθήνα"
        area = locality or sublocality or admin3
    else:
        raw_city = locality or admin3 or _get_component(components, "administrative_area_level_2")
        city = resolve_greek_city(raw_city, postal_code)
        area = sublocality or admin3 or locality

    return ParsedDeliveryAddress(
        city=city,
        area=(area or "").strip(),
        street=(route or "").strip(),
        street_number=(street_number or "").strip(),
        postal_code=postal_code,
    )


def parse_address_components_json(raw_json: str) -> ParsedDeliveryAddress | None:
    if not (raw_json or "").strip():
        return None
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    return parse_google_address_components(payload)


def fetch_greek_address_components(place_id: str) -> list[dict[str, Any]] | None:
    """Re-fetch address components from Google in Greek (el) for a place_id."""
    api_key = (getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "").strip()
    normalized_place_id = (place_id or "").strip()
    if not normalized_place_id or not api_key:
        return None

    query = urlencode(
        {
            "place_id": normalized_place_id,
            "language": "el",
            "region": "gr",
            "key": api_key,
        }
    )
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{query}"
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    if payload.get("status") != "OK" or not payload.get("results"):
        return None

    components = payload["results"][0].get("address_components")
    if not isinstance(components, list):
        return None
    return components


def parse_address_from_place_id(place_id: str) -> ParsedDeliveryAddress | None:
    components = fetch_greek_address_components(place_id)
    if not components:
        return None
    return parse_google_address_components(components)


def apply_parsed_address_to_user(user, parsed: ParsedDeliveryAddress) -> None:
    user.city = parsed.city
    user.area = parsed.area
    user.street = parsed.street
    user.street_number = parsed.street_number
    user.postal_code = parsed.postal_code
    user.address = parsed.address
