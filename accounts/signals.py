from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from accounts.emails import send_welcome_email


@receiver(user_signed_up)
def _send_welcome_email_on_signup(request, user, **kwargs):
    send_welcome_email(user)
