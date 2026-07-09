import os

from django.conf import settings
from django.urls import reverse

from allauth.socialaccount.providers.google.provider import GoogleProvider
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter


class KokkorisGoogleOAuth2Adapter(GoogleOAuth2Adapter):
    """
    OAuth callback URL helper for local development.

    Google treats localhost and 127.0.0.1 as different redirect URIs. Register
    both in Google Cloud Console, or set GOOGLE_OAUTH_REDIRECT_URI in .env to
    force one canonical callback URL.
    """

    def get_callback_url(self, request, app):
        explicit = os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip()
        if explicit:
            return explicit
        return super().get_callback_url(request, app)


class KokkorisGoogleProvider(GoogleProvider):
    package = "allauth.socialaccount.providers.google"
    oauth2_adapter_class = KokkorisGoogleOAuth2Adapter
