from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from newsletter.models import NewsletterSubscriber

User = get_user_model()


class SignupNewsletterApiTests(TestCase):
    def test_signup_with_newsletter_checked_subscribes_user(self):
        response = self.client.post(
            reverse("accounts:api_signup"),
            data={
                "email": "signup-news@example.com",
                "phone_number": "6912345678",
                "password1": "securepass123",
                "password2": "securepass123",
                "newsletter_subscribe": True,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            NewsletterSubscriber.objects.filter(
                email="signup-news@example.com",
                is_active=True,
            ).exists()
        )

    def test_signup_without_newsletter_does_not_subscribe(self):
        response = self.client.post(
            reverse("accounts:api_signup"),
            data={
                "email": "signup-no-news@example.com",
                "phone_number": "6998765432",
                "password1": "securepass123",
                "password2": "securepass123",
                "newsletter_subscribe": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            NewsletterSubscriber.objects.filter(email="signup-no-news@example.com").exists()
        )
