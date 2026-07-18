"""Tests for package-size display formatting."""
from decimal import Decimal

from django.test import SimpleTestCase

from products.catalog import format_weight


class FormatWeightTests(SimpleTestCase):
    def test_under_one_kg_uses_grams(self):
        self.assertEqual(format_weight(Decimal("0.085"), "kg"), "85 g")
        self.assertEqual(format_weight(Decimal("0.08"), "kg"), "80 g")
        self.assertEqual(format_weight(Decimal("0.5"), "kg"), "500 g")

    def test_one_kg_and_above_keep_kg(self):
        self.assertEqual(format_weight(Decimal("1"), "kg"), "1 kg")
        self.assertEqual(format_weight(Decimal("2.5"), "kg"), "2,5 kg")
        self.assertEqual(format_weight(Decimal("10"), "kg"), "10 kg")
        self.assertEqual(format_weight(Decimal("18"), "kg"), "18 kg")

    def test_litter_under_one_litre_uses_ml(self):
        self.assertEqual(format_weight(Decimal("0.5"), "L"), "500 ml")
        self.assertEqual(format_weight(Decimal("2"), "L"), "2 L")
