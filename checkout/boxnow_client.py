"""
Box Now Partner API client (OAuth 2.0 client credentials).

Docs: https://boxnow.gr/en/partner-api
"""
import logging
import time

import requests
from django.conf import settings

from checkout.boxnow_pricing import cart_weight_grams, determine_compartment_size

logger = logging.getLogger(__name__)

_token_cache = {"access_token": None, "expires_at": 0.0}


class BoxNowAPIError(Exception):
    """Raised when a Box Now API call fails."""


def boxnow_api_enabled():
    return bool(
        settings.BOXNOW_OAUTH_CLIENT_ID
        and settings.BOXNOW_OAUTH_CLIENT_SECRET
        and settings.BOXNOW_API_URL
        and settings.BOXNOW_ORIGIN_LOCATION_ID
    )


def _clear_token_cache():
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0.0


def _get_access_token():
    now = time.time()
    if _token_cache["access_token"] and now < _token_cache["expires_at"] - 30:
        return _token_cache["access_token"]

    url = f"{settings.BOXNOW_API_URL.rstrip('/')}/api/v1/auth-sessions"
    response = requests.post(
        url,
        json={
            "grant_type": "client_credentials",
            "client_id": settings.BOXNOW_OAUTH_CLIENT_ID,
            "client_secret": settings.BOXNOW_OAUTH_CLIENT_SECRET,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise BoxNowAPIError(
            f"Box Now auth failed ({response.status_code}): {response.text[:500]}"
        )

    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise BoxNowAPIError("Box Now auth response missing access_token")

    expires_in = int(payload.get("expires_in", 3600))
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


def _api_request(method, base_url, path, *, params=None, json_body=None):
    token = _get_access_token()
    url = f"{base_url.rstrip('/')}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"

    response = requests.request(
        method,
        url,
        headers=headers,
        params=params,
        json=json_body,
        timeout=30,
    )
    if response.status_code == 401:
        _clear_token_cache()
        raise BoxNowAPIError("Box Now API unauthorized — check OAuth credentials.")
    if response.status_code >= 400:
        raise BoxNowAPIError(
            f"Box Now API {method} {path} failed ({response.status_code}): "
            f"{response.text[:500]}"
        )
    if not response.content:
        return {}
    return response.json()


def list_destinations(*, latlng=None, radius=25000, required_size=None):
    """List APM locker destinations (optional — widget handles selection in checkout)."""
    params = {"radius": radius}
    if latlng:
        params["latlng"] = latlng
    if required_size:
        params["requiredSize"] = required_size
    payload = _api_request(
        "GET",
        settings.BOXNOW_LOCATION_API_URL,
        "/api/v1/destinations",
        params=params,
    )
    return payload.get("data", [])


def create_delivery_request_for_order(order):
    """
    Register a Box Now delivery after checkout.

    Returns the API response dict (id + parcel ids) and updates the order.
    """
    if not boxnow_api_enabled():
        raise BoxNowAPIError("Box Now API is not fully configured.")

    if not order.boxnow_locker_id:
        raise BoxNowAPIError(f"Order {order.order_code} has no Box Now locker.")

    items = list(order.items.select_related("product_variant__product"))
    compartment_size = determine_compartment_size(items)
    weight_grams = cart_weight_grams(items)

    is_cod = order.payment_method == order.PAYMENT_METHOD_COD
    payment_mode = "cod" if is_cod else "prepaid"
    amount_collected = str(order.total_cost) if is_cod else "0.00"

    contact_name = order.user.get_full_name() or order.user.email
    origin_contact = settings.BOXNOW_ORIGIN_CONTACT_NAME or contact_name
    origin_phone = settings.BOXNOW_ORIGIN_CONTACT_PHONE or order.delivery_phone_number
    origin_email = settings.BOXNOW_ORIGIN_CONTACT_EMAIL or settings.DEFAULT_FROM_EMAIL

    body = {
        "orderNumber": order.order_code,
        "invoiceValue": str(order.total_cost),
        "paymentMode": payment_mode,
        "amountToBeCollected": amount_collected,
        "origin": {
            "contactNumber": origin_phone,
            "contactEmail": origin_email,
            "contactName": origin_contact,
            "locationId": settings.BOXNOW_ORIGIN_LOCATION_ID,
        },
        "destination": {
            "contactNumber": order.delivery_phone_number,
            "contactEmail": order.user.email,
            "contactName": contact_name,
            "locationId": order.boxnow_locker_id,
        },
        "items": [
            {
                "name": f"Παραγγελία {order.order_code}",
                "value": str(order.cart_cost),
                "compartmentSize": compartment_size,
                "weight": weight_grams,
            }
        ],
    }
    if settings.BOXNOW_NOTIFY_EMAIL:
        body["notifyOnAccepted"] = settings.BOXNOW_NOTIFY_EMAIL

    payload = _api_request(
        "POST",
        settings.BOXNOW_API_URL,
        "/api/v1/delivery-requests",
        json_body=body,
    )

    parcel_id = ""
    parcels = payload.get("parcels") or []
    if parcels:
        parcel_id = str(parcels[0].get("id", ""))

    order.boxnow_delivery_request_id = str(payload.get("id", ""))
    order.boxnow_parcel_id = parcel_id
    order.save(
        update_fields=["boxnow_delivery_request_id", "boxnow_parcel_id"]
    )
    return payload
