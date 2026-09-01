"""Tests for free-shipping promotion messaging."""
from decimal import Decimal

from django.test import SimpleTestCase, override_settings

from products.shipping_promo import (
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
