"""Greek mobile phone validation (backend only)."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

from core import user_text

# National mobile numbers: 10 digits starting with 69X (X = 0–9).
_MOBILE_PREFIX_2 = "69"
_MOBILE_PREFIX_3 = tuple(f"69{digit}" for digit in "0123456789")
_NATIONAL_LENGTH = 10

_LETTERS_RE = re.compile(r"[A-Za-zΑ-Ωα-ωίϊΐόύϋΰήώ]")
_ALLOWED_CHARS_RE = re.compile(r"^[\d\s+\-().]+$")


def validate_greek_mobile(raw: str | None) -> str:
    """
    Validate and normalize a Greek mobile number to 10-digit national format.

    Accepts optional country prefix (+30 / 0030 / 30). Rejects letters and
    non-mobile prefixes. Raises ValidationError on failure.
    """
    if raw is None or not str(raw).strip():
        raise ValidationError(user_text.PHONE_REQUIRED, code="phone_required")

    text = str(raw).strip()

    if _LETTERS_RE.search(text):
        raise ValidationError(user_text.PHONE_DIGITS, code="phone_letters")

    if not _ALLOWED_CHARS_RE.fullmatch(text):
        raise ValidationError(user_text.PHONE_DIGITS, code="phone_invalid_chars")

    digits = re.sub(r"\D", "", text)
    if not digits:
        raise ValidationError(user_text.PHONE_REQUIRED, code="phone_required")

    if digits.startswith("0030"):
        digits = digits[4:]
    elif digits.startswith("30") and len(digits) > _NATIONAL_LENGTH:
        digits = digits[2:]

    if len(digits) != _NATIONAL_LENGTH:
        raise ValidationError(user_text.PHONE_LENGTH, code="phone_length")

    if not digits.startswith(_MOBILE_PREFIX_2):
        raise ValidationError(user_text.PHONE_PREFIX, code="phone_prefix_2")

    prefix3 = digits[:3]
    if prefix3 not in _MOBILE_PREFIX_3:
        raise ValidationError(user_text.PHONE_INVALID, code="phone_prefix_3")

    return digits
