from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class SignupPhoneApiTests(TestCase):
    def _signup(self, **overrides):
        payload = {
            "email": "signup-phone@example.com",
            "phone_number": "6912345678",
            "password1": "securepass123",
            "password2": "securepass123",
            "newsletter_subscribe": False,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("accounts:api_signup"),
            data=payload,
            content_type="application/json",
        )

    def test_signup_saves_valid_greek_mobile(self):
        response = self._signup()
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(email="signup-phone@example.com")
        self.assertEqual(user.phone_number, "6912345678")

    def test_signup_rejects_missing_phone(self):
        response = self._signup(phone_number="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("phone_number", response.json()["errors"])

    def test_signup_rejects_letters_in_phone(self):
        response = self._signup(phone_number="69abc12345")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Μόνο αριθμοί", response.json()["errors"]["phone_number"][0])

    def test_signup_rejects_invalid_mobile_prefix(self):
        response = self._signup(phone_number="6812345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("69", response.json()["errors"]["phone_number"][0])
