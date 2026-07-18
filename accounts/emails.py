"""Transactional emails for customer accounts."""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse

User = get_user_model()


def _site_base_url() -> str:
    return getattr(settings, "SITE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def welcome_display_name(user: User) -> str:
    """Greeting name for welcome email."""
    first = (user.first_name or "").strip()
    if first:
        return first
    email = (user.email or "").strip()
    if email and "@" in email:
        return email.split("@", 1)[0]
    return "φίλε/η μας"


def build_welcome_email_context(user: User) -> dict:
    shop_url = f"{_site_base_url()}{reverse('products:all')}"
    return {
        "site_name": "Kokkoris Pet Food",
        "display_name": welcome_display_name(user),
        "shop_url": shop_url,
        "site_url": _site_base_url(),
    }


def send_welcome_email(user: User) -> bool:
    """Send welcome email after a new account is created."""
    recipient = (user.email or "").strip()
    if not recipient:
        return False

    context = build_welcome_email_context(user)
    subject = "Καλώς ήρθατε στο Kokkoris Pet Food!"
    text_body = render_to_string("emails/welcome.txt", context)
    html_body = render_to_string("emails/welcome.html", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, "text/html")
    message.send(fail_silently=False)
    return True
