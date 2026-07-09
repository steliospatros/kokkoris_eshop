from allauth.account.utils import user_field
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class KokkorisSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Social login adapter for Kokkoris Eshop.

    Connects existing accounts by verified email (via SOCIALACCOUNT_EMAIL_AUTHENTICATION)
    and fills first/last name from Google profile data on signup.
    """

    error_messages = {
        **DefaultSocialAccountAdapter.error_messages,
        "email_taken": (
            "Υπάρχει ήδη λογαριασμός με αυτό το email. "
            "Συνδέσου πρώτα με email/κωδικό και μετά σύνδεσε τον λογαριασμό Google."
        ),
        "invalid_token": "Μη έγκυρο token σύνδεσης. Δοκίμασε ξανά.",
        "no_password": "Ο λογαριασμός σου δεν έχει κωδικό.",
        "no_verified_email": "Ο λογαριασμός σου δεν έχει επαληθευμένο email.",
        "disconnect_last": "Δεν μπορείς να αποσυνδέσεις τον τελευταίο λογαριασμό κοινωνικής σύνδεσης.",
        "connected_other": "Αυτός ο λογαριασμός Google είναι ήδη συνδεδεμένος με άλλο προφίλ.",
    }

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        extra = {}
        if sociallogin.account:
            extra = sociallogin.account.extra_data or {}

        if not user_field(user, "first_name"):
            user_field(user, "first_name", data.get("first_name") or extra.get("given_name") or "")
        if not user_field(user, "last_name"):
            user_field(user, "last_name", data.get("last_name") or extra.get("family_name") or "")

        return user
