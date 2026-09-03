"""
BOX NOW parcel webhooks (CloudEvents + HMAC SHA-256 of the raw `data` object).

Guide: Webhook-Based Parcel Tracking Guide v1.4.6
OpenAPI: partner-api-1.68.yaml  POST /{your-webhook-endpoint}
"""
import hashlib
import hmac
import json
import logging
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils.dateparse import parse_datetime

from orders.models import Order

logger = logging.getLogger(__name__)

BOXNOW_EVENT_LABELS = {
    "new": "Η αποστολή BOX NOW καταχωρήθηκε.",
    "in-depot": "Το δέμα βρίσκεται σε αποθήκη BOX NOW.",
    "final-destination": "Το δέμα έφτασε στο locker και περιμένει παραλαβή.",
    "delivered": "Το δέμα παραλήφθηκε από το locker.",
    "expired": "Το δέμα έληξε στο locker και επιστρέφει στον αποστολέα.",
    "returned": "Το δέμα επιστράφηκε στον αποστολέα.",
    "canceled": "Η αποστολή BOX NOW ακυρώθηκε.",
    "accepted-for-return": "Το δέμα έγινε δεκτό για επιστροφή.",
    "missing": "Ο courier BOX NOW δεν παρέλαβε το δέμα.",
    "accepted-to-locker": "Το δέμα έγινε δεκτό στο locker αποστολής.",
    "lost": "Το δέμα δηλώθηκε ως απολεσθέν.",
}


class BoxNowWebhookError(Exception):
    """Invalid or unverifiable webhook payload."""


def _raw_data_object(raw_text):
    """Slice the `data` JSON object from the raw body without reformatting it."""
    marker = raw_text.find('"data"')
    if marker < 0:
        raise BoxNowWebhookError("Webhook payload missing data.")
    brace = raw_text.find("{", marker)
    if brace < 0:
        raise BoxNowWebhookError("Webhook data is not an object.")
    decoder = json.JSONDecoder()
    _, end = decoder.raw_decode(raw_text, brace)
    return raw_text[brace:end]


def verify_boxnow_signature(raw_body, datasignature):
    secret = (settings.BOXNOW_WEBHOOK_SECRET or "").strip()
    if not secret:
        return True
    if not datasignature:
        raise BoxNowWebhookError("Missing datasignature.")
    raw_text = raw_body.decode("utf-8") if isinstance(raw_body, bytes) else raw_body
    digest = hmac.new(
        secret.encode("utf-8"),
        _raw_data_object(raw_text).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest.lower(), str(datasignature).lower()):
        raise BoxNowWebhookError("Invalid datasignature.")
    return True


def apply_boxnow_parcel_event(payload):
    """
    Persist the latest parcel event on the matching order.

    Uses data.event (not parcelState) per the tracking guide, and data.time
    to ignore stale/duplicate deliveries.
    """
    data = payload.get("data") or {}
    event = (data.get("event") or "").strip()
    order_number = (data.get("orderNumber") or "").strip()
    parcel_id = str(data.get("parcelId") or payload.get("subject") or "")
    parcel_state = (data.get("parcelState") or "").strip()
    pin = str(data.get("parcelPin") or "")

    if not order_number:
        raise BoxNowWebhookError("Webhook data missing orderNumber.")

    event_at = parse_datetime(str(data.get("time") or payload.get("time") or ""))
    if event_at and event_at.tzinfo is None:
        event_at = event_at.replace(tzinfo=dt_timezone.utc)

    try:
        order = Order.objects.get(order_code=order_number)
    except Order.DoesNotExist:
        logger.warning("BOX NOW webhook for unknown order %s", order_number)
        return None

    if order.boxnow_last_event_at and event_at and event_at <= order.boxnow_last_event_at:
        return order

    update_fields = ["boxnow_last_event", "boxnow_parcel_state"]
    order.boxnow_last_event = event
    order.boxnow_parcel_state = parcel_state or event
    if parcel_id:
        order.boxnow_parcel_id = parcel_id
        update_fields.append("boxnow_parcel_id")
    if pin:
        order.boxnow_parcel_pin = pin
        update_fields.append("boxnow_parcel_pin")
    if event_at:
        order.boxnow_last_event_at = event_at
        update_fields.append("boxnow_last_event_at")

    if event == "delivered" and order.status != Order.STATUS_CANCELLED:
        order.status = Order.STATUS_DELIVERED
        update_fields.append("status")

    order.save(update_fields=update_fields)
    return order
