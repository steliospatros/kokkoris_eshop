from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.emails import send_welcome_email, welcome_display_name

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_BASE_URL="http://testserver",
)
class WelcomeEmailTests(TestCase):
    def test_welcome_display_name_uses_first_name(self):
        user = User(first_name="Μαρία", email="maria@example.com")
        self.assertEqual(welcome_display_name(user), "Μαρία")

    def test_send_welcome_email_contains_greeting_and_shop_link(self):
        user = User.objects.create_user(
            email="welcome@example.com",
            password="securepass123",
            first_name="Γιάννης",
        )
        mail.outbox.clear()
        send_welcome_email(user)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Καλώς ήρθατε στο Kokkoris Pet Food!")
        body = mail.outbox[0].body
        self.assertIn("Αγαπητέ/ή Γιάννης", body)
        self.assertIn("Περιηγηθείτε στο Κατάστημα", body)
        self.assertIn("210 6038727", body)
        self.assertIn(reverse("products:all"), body)

    def test_signup_sends_welcome_email(self):
        mail.outbox.clear()
        response = self.client.post(
            reverse("accounts:api_signup"),
            data={
                "email": "signup-welcome@example.com",
                "phone_number": "6912345678",
                "password1": "securepass123",
                "password2": "securepass123",
                "newsletter_subscribe": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        welcome_messages = [
            message
            for message in mail.outbox
            if "Καλώς ήρθατε" in message.subject
        ]
        self.assertEqual(len(welcome_messages), 1)
