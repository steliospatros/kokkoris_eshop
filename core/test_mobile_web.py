from django.test import TestCase
from django.urls import reverse


class MobileStorefrontChromeTests(TestCase):
    def test_home_exposes_phone_catalog_menu(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="nav-browse-toggle"')
        self.assertContains(response, 'id="nav-browse-panel"')
        self.assertContains(response, "mobile-web.css")
        self.assertContains(response, reverse("products:dogs"))
        self.assertContains(response, reverse("products:cats"))
        self.assertContains(response, reverse("products:all"))
        self.assertContains(response, reverse("products:brands"))

    def test_catalog_exposes_phone_filter_toggle(self):
        response = self.client.get(reverse("products:all"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="catalog-filters-toggle"')
        self.assertContains(response, 'id="catalog-filters-panel"')
        self.assertContains(response, "catalog-layout")

    def test_viewport_allows_notch_safe_area(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "viewport-fit=cover")
