"""Outbound SMS via Twilio REST API."""
from __future__ import annotations

import logging

import requests
from django.conf import settings

from core import user_text

logger = logging.getLogger("kokkoris")

# Customer-facing copy only. Technical Twilio details stay in logs.
TWILIO_ERROR_MESSAGES = {
    "21211": user_text.PHONE_INVALID,
    "21214": user_text.SMS_NOT_ACCEPTED,
    "21610": user_text.SMS_OPTED_OUT,
    "21614": user_text.PHONE_INVALID,
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
            return user_text.SMS_UNAVAILABLE
    except (ValueError, TypeError):
        pass
    return user_text.SMS_UNAVAILABLE


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
        raise SMSDeliveryError(user_text.SMS_UNAVAILABLE) from None

    if response.status_code >= 400:
        error = _parse_twilio_error(response)
        logger.error("Twilio %s for %s: %s", response.status_code, to_greek_mobile, response.text[:300])
        raise SMSDeliveryError(error)
