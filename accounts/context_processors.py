import os

from django.urls import reverse

from accounts.password_help import PASSWORD_RULES


def _google_oauth_ready():
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
    if client_id and secret:
        return True
    try:
        from allauth.socialaccount.models import SocialApp

        return SocialApp.objects.filter(provider="google").exclude(client_id="").exclude(
            secret=""
        ).exists()
    except Exception:
        return False


def auth_helpers(request):
    from django.conf import settings

    google_ready = _google_oauth_ready()
    return {
        "password_rules": PASSWORD_RULES,
        "google_oauth_ready": google_ready,
        "google_login_url": reverse("google_login") if google_ready else "",
        "phone_verification_enabled": getattr(settings, "PHONE_VERIFICATION_ENABLED", False),
    }
