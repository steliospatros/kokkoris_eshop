"""SMS OTP for Greek mobile verification."""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError

from accounts.phone_validation import validate_greek_mobile
from accounts.sms import SMSDeliveryError, is_sms_configured, send_sms

logger = logging.getLogger(__name__)

OTP_CACHE_PREFIX = "phone_otp:"
OTP_SEND_COOLDOWN_PREFIX = "phone_otp_cooldown:"
OTP_TTL_SECONDS = 600
SEND_COOLDOWN_SECONDS = 60


def phone_verification_enabled() -> bool:
    return bool(getattr(settings, "PHONE_VERIFICATION_ENABLED", False))


def effective_phone_verified(user) -> bool:
    """True when verification is off or the user completed SMS verification."""
    if not phone_verification_enabled():
        return True
    return bool(getattr(user, "phone_verified_at", None))


@dataclass
class SendOTPResult:
    phone: str
    sms_sent: bool


def _cache_key(phone: str) -> str:
    return f"{OTP_CACHE_PREFIX}{phone}"


def _cooldown_key(user_id: int) -> str:
    return f"{OTP_SEND_COOLDOWN_PREFIX}{user_id}"


def _validation_message(exc: ValidationError) -> str:
    if getattr(exc, "messages", None):
        return str(exc.messages[0])
    if getattr(exc, "message", None):
        return str(exc.message)
    return "Μη έγκυρος αριθμός κινητού."


def check_send_cooldown(user_id: int) -> int | None:
    """Return remaining cooldown seconds, or None if send is allowed."""
    expires = cache.get(_cooldown_key(user_id))
    if not expires:
        return None
    import time

    remaining = int(expires - time.time())
    return remaining if remaining > 0 else None


def send_otp(phone: str, *, user_id: int) -> SendOTPResult:
    """Generate, store and send a 6-digit OTP."""
    try:
        normalized = validate_greek_mobile(phone)
    except ValidationError as exc:
        raise ValidationError(_validation_message(exc)) from exc

    remaining = check_send_cooldown(user_id)
    if remaining:
        raise ValidationError(
            f"Περίμενε {remaining}s.",
            code="otp_cooldown",
        )

    code = f"{random.randint(0, 999999):06d}"
    cache.set(_cache_key(normalized), code, OTP_TTL_SECONDS)

    import time

    cache.set(_cooldown_key(user_id), time.time() + SEND_COOLDOWN_SECONDS, SEND_COOLDOWN_SECONDS)

    message = f"Kokkoris Pet Food: ο κωδικός σου είναι {code}. Ισχύει 10 λεπτά."

    if not phone_verification_enabled():
        raise SMSDeliveryError("Η επιβεβαίωση κινητού δεν είναι ενεργή.")

    if not is_sms_configured():
        cache.delete(_cache_key(normalized))
        raise SMSDeliveryError("Η αποστολή SMS δεν είναι διαθέσιμη.")

    try:
        send_sms(normalized, message)
    except SMSDeliveryError:
        cache.delete(_cache_key(normalized))
        raise

    return SendOTPResult(phone=normalized, sms_sent=True)


def verify_otp(phone: str, code: str) -> str:
    """
    Verify OTP. Returns normalized phone on success.
    Raises ValidationError with a user-facing message on failure.
    """
    raw_code = (code or "").strip()
    if not raw_code:
        raise ValidationError("Συμπλήρωσε τον κωδικό.", code="otp_required")
    if not raw_code.isdigit() or len(raw_code) != 6:
        raise ValidationError("6 ψηφία απαιτούνται.", code="otp_format")

    try:
        normalized = validate_greek_mobile(phone)
    except ValidationError as exc:
        raise ValidationError(_validation_message(exc)) from exc

    expected = cache.get(_cache_key(normalized))
    if not expected:
        raise ValidationError("Ο κωδικός έληξε. Στείλε νέο SMS.", code="otp_expired")
    if raw_code != str(expected):
        raise ValidationError("Λάθος κωδικός.", code="otp_invalid")

    cache.delete(_cache_key(normalized))
    return normalized
