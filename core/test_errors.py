import json

from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from core import user_text
from core.views import csrf_failure, server_error


class ErrorPageTests(TestCase):
    def test_unknown_url_shows_friendly_404(self):
        response = self.client.get("/selida-pou-den-yparxei/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, user_text.ERROR_404_TITLE, status_code=404)
        self.assertContains(response, user_text.HOME_LINK, status_code=404)

    def test_server_error_page_is_self_contained(self):
        request = RequestFactory().get("/")
        response = server_error(request)
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, user_text.ERROR_500_TITLE, status_code=500)

    def test_404_handler_copy(self):
        response = self.client.get("/selida-pou-den-yparxei/")
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "Not Found", status_code=404)

    def test_json_csrf_failure_stays_json(self):
        request = RequestFactory().post(
            "/cart/add/",
            data=json.dumps({"variant_id": 1}),
            content_type="application/json",
        )
        response = csrf_failure(request, reason="token missing")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        payload = json.loads(response.content.decode())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], user_text.AUTH_SESSION_EXPIRED)
        self.assertEqual(payload["code"], "AUTH_SESSION_EXPIRED")

    def test_cart_add_without_csrf_returns_json(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse("cart:add"),
            data=json.dumps({"variant_id": 1}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Content-Type"].split(";")[0], "application/json")
        payload = json.loads(response.content.decode())
        self.assertEqual(payload["error"], user_text.AUTH_SESSION_EXPIRED)
