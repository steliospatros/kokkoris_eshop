"""Tests for free-shipping promotion messaging."""
from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from products.shipping_promo import (
    build_athens_delivery_promo,
    build_free_shipping_promo,
    build_static_free_shipping_promo,
)


@override_settings(FREE_SHIPPING_ORDER_MINIMUM=Decimal("60.00"))
class FreeShippingPromoTests(SimpleTestCase):
    def test_remaining_amount_message(self):
        promo = build_free_shipping_promo(Decimal("25.00"))
        self.assertFalse(promo["qualified"])
        self.assertEqual(promo["remaining"], Decimal("35.00"))
        self.assertIn("35,00", promo["message"])
        self.assertIn("δωρεάν μεταφορικά", promo["message"].lower())

    def test_qualified_message(self):
        promo = build_free_shipping_promo(Decimal("65.00"))
        self.assertTrue(promo["qualified"])
        self.assertEqual(promo["remaining"], Decimal("0.00"))
        self.assertIn("δωρεάν", promo["message"].lower())

    def test_default_minimum_is_60(self):
        from django.test import override_settings as _override

        with _override(FREE_SHIPPING_ORDER_MINIMUM=Decimal("60.00")):
            promo = build_free_shipping_promo(Decimal("0.00"))
        self.assertEqual(promo["minimum"], Decimal("60.00"))
        self.assertIn("60,00", promo["headline"])

    def test_static_homepage_copy_has_no_elta(self):
        promo = build_static_free_shipping_promo()
        self.assertIn("courier", promo["message"].lower())
        self.assertIn("BOX NOW", promo["message"])
        self.assertNotIn("ELTA", promo["message"])
        self.assertNotIn("ΕΛΤΑ", promo["message"])

    def test_athens_delivery_promo_mentions_four_business_days(self):
        promo = build_athens_delivery_promo()
        self.assertIn("εντός Αθηνών", promo["strip_headline"])
        self.assertIn("έως 3 εργάσιμες", promo["message"])


class HomepageAthensPromoTests(TestCase):
    def test_homepage_advertises_free_athens_delivery(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Δωρεάν παράδοση εντός Αθηνών")
        self.assertContains(response, "έως 3 εργάσιμες")
        self.assertContains(response, "home-hero-promos")
        self.assertContains(response, "Αθήνα")
        self.assertContains(response, "Όλη η Ελλάδα")
        self.assertContains(response, "Καλωσήρθατε στην σελίδα μας")
        html = response.content.decode()
        welcome_at = html.find("home-hero-welcome")
        promos_at = html.find("home-hero-promos")
        self.assertGreater(welcome_at, 0)
        self.assertGreater(promos_at, welcome_at)
