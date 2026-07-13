import re
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.phone_verification import send_otp, verify_otp


class PhoneVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            email="phone@example.com",
            password="pass12345",
        )
        self.client = Client()
        self.client.force_login(self.user)

    @patch("accounts.phone_verification.send_sms")
    @override_settings(
        PHONE_VERIFICATION_ENABLED=True,
        TWILIO_ACCOUNT_SID="ACtest",
        TWILIO_AUTH_TOKEN="token",
        TWILIO_PHONE_NUMBER="+306900000000",
    )
    def test_send_and_verify_otp(self, mock_send_sms):
        result = send_otp("6912345678", user_id=self.user.pk)
        self.assertEqual(result.phone, "6912345678")
        self.assertTrue(result.sms_sent)
        mock_send_sms.assert_called_once()
        message = mock_send_sms.call_args[0][1]
        code = re.search(r"(\d{6})", message).group(1)
        normalized = verify_otp("6912345678", code)
        self.assertEqual(normalized, "6912345678")

    def test_send_otp_rejects_invalid_phone(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            send_otp("123", user_id=self.user.pk)

    @override_settings(PHONE_VERIFICATION_ENABLED=True)
    def test_api_send_returns_greek_error_for_bad_phone(self):
        response = self.client.post(
            reverse("accounts:api_phone_send_otp"),
            data='{"phone_number": "123"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("ψηφία", data["error"])

    @patch("accounts.phone_verification.send_sms")
    @override_settings(
        PHONE_VERIFICATION_ENABLED=True,
        TWILIO_ACCOUNT_SID="ACtest",
        TWILIO_AUTH_TOKEN="token",
        TWILIO_PHONE_NUMBER="+306900000000",
    )
    def test_api_send_and_verify(self, mock_send_sms):
        response = self.client.post(
            reverse("accounts:api_phone_send_otp"),
            data='{"phone_number": "6912345678"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["sms_sent"])

        code = re.search(r"(\d{6})", mock_send_sms.call_args[0][1]).group(1)
        verify_response = self.client.post(
            reverse("accounts:api_phone_verify_otp"),
            data='{"phone_number": "6912345678", "code": "' + code + '"}',
            content_type="application/json",
        )
        self.assertEqual(verify_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.phone_verified_at)

    @patch("accounts.phone_verification.send_sms")
    @override_settings(
        PHONE_VERIFICATION_ENABLED=True,
        TWILIO_ACCOUNT_SID="ACtest",
        TWILIO_AUTH_TOKEN="token",
        TWILIO_PHONE_NUMBER="+306900000000",
    )
    def test_api_verify_wrong_code(self, mock_send_sms):
        send_otp("6912345678", user_id=self.user.pk)
        response = self.client.post(
            reverse("accounts:api_phone_verify_otp"),
            data='{"phone_number": "6912345678", "code": "000000"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Λάθος", response.json()["error"])
