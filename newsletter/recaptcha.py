import requests
from django.conf import settings


def verify_recaptcha(token, remote_ip=None):
    """
    Verify a Google reCAPTCHA v3 token.

    Returns True when reCAPTCHA is disabled (no keys configured) or when
    Google accepts the token with a score above the configured threshold.
    """
    if not settings.RECAPTCHA_ENABLED:
        return True

    if not token:
        return False

    try:
        response = requests.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": token,
                "remoteip": remote_ip or "",
            },
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        return False

    result = response.json()
    if not result.get("success"):
        return False

    action = result.get("action")
    if action and action != settings.RECAPTCHA_ACTION:
        return False

    score = result.get("score", 0)
    return score >= settings.RECAPTCHA_SCORE_THRESHOLD
