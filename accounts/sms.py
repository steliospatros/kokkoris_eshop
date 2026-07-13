"""Outbound SMS via Twilio REST API."""
from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TWILIO_ERROR_MESSAGES = {
    "21211": "Μη έγκυρος αριθμός.",
    "21214": "Ο αριθμός δεν δέχεται SMS.",
    "21606": "Ο αριθμός δεν είναι εξουσιοδοτημένος (δοκιμαστικός λογαριασμός).",
    "21608": "Η αποστολή SMS δεν είναι ενεργή για αυτή τη χώρα.",
    "21610": "Ο αριθμός έχει απορρίψει SMS.",
    "21614": "Μη έγκυρος αριθμός παραλήπτη.",
    "21612": (
        "Ο US αριθμός (+1) δεν μπορεί να στείλει στην Ελλάδα. "
        "Χρειάζεται Alphanumeric Sender ή upgrade λογαριασμού."
    ),
    "21267": "Alphanumeric sender δεν επιτρέπεται σε trial — κάνε upgrade στο Twilio.",
    "21659": "Λάθος αριθμός αποστολής στο .env — χρειάζεσαι Twilio number, όχι verified caller ID.",
    "21408": "Δεν επιτρέπεται SMS σε αυτή την περιοχή.",
    "20003": "Λάθος Twilio credentials — έλεγξε SID/token στο .env.",
    "30032": "Ο αριθμός δεν είναι εξουσιοδοτημένος (δοκιμαστικός λογαριασμός).",
}


class SMSDeliveryError(Exception):
    """SMS could not be delivered."""


def is_sms_configured() -> bool:
    return bool(
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and (
            settings.TWILIO_MESSAGING_SERVICE_SID
            or settings.TWILIO_ALPHANUMERIC_SENDER
            or settings.TWILIO_PHONE_NUMBER
        )
    )


def format_phone_e164(greek_mobile: str) -> str:
    """10-digit national mobile (69XXXXXXXX) → +3069XXXXXXXX."""
    return f"+30{greek_mobile}"


def _sender_for_greece() -> tuple[str, str]:
    """Return (payload_key, sender_value) for outbound Greek SMS."""
    if settings.TWILIO_MESSAGING_SERVICE_SID:
        return "MessagingServiceSid", settings.TWILIO_MESSAGING_SERVICE_SID
    if settings.TWILIO_ALPHANUMERIC_SENDER:
        return "From", settings.TWILIO_ALPHANUMERIC_SENDER
    return "From", settings.TWILIO_PHONE_NUMBER


def _parse_twilio_error(response: requests.Response) -> str:
    try:
        payload = response.json()
        code = str(payload.get("code") or "")
        if code in TWILIO_ERROR_MESSAGES:
            return TWILIO_ERROR_MESSAGES[code]
        message = (payload.get("message") or "").strip()
        if "unverified" in message.lower():
            return TWILIO_ERROR_MESSAGES["30032"]
    except (ValueError, TypeError):
        pass
    return "Δεν στάλθηκε SMS. Δοκίμασε ξανά."


def send_sms(to_greek_mobile: str, body: str) -> None:
    """Send SMS to normalized Greek mobile (69XXXXXXXX)."""
    if not is_sms_configured():
        logger.info("Twilio not configured — skip send to %s", to_greek_mobile)
        return

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
    )
    sender_key, sender_value = _sender_for_greece()
    payload = {
        "To": format_phone_e164(to_greek_mobile),
        "Body": body,
        sender_key: sender_value,
    }

    try:
        response = requests.post(
            url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            data=payload,
            timeout=15,
        )
    except requests.RequestException:
        logger.exception("Twilio request failed for %s", to_greek_mobile)
        raise SMSDeliveryError("Δεν στάλθηκε SMS. Δοκίμασε ξανά.") from None

    if response.status_code >= 400:
        error = _parse_twilio_error(response)
        logger.error("Twilio %s for %s: %s", response.status_code, to_greek_mobile, response.text[:300])
        raise SMSDeliveryError(error)
