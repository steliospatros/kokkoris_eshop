from django.test import RequestFactory, TestCase

from core import user_text
from core.views import server_error


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
