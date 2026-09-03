from decimal import Decimal

from django.test import SimpleTestCase

from products.pricing import ceil_to_tenth


class CeilToTenthTests(SimpleTestCase):
    def test_raises_to_next_tenth(self):
        self.assertEqual(ceil_to_tenth(Decimal("0.85")), Decimal("0.90"))
        self.assertEqual(ceil_to_tenth(Decimal("0.81")), Decimal("0.90"))
        self.assertEqual(ceil_to_tenth(Decimal("1.01")), Decimal("1.10"))
        self.assertEqual(ceil_to_tenth("9.38"), Decimal("9.40"))

    def test_already_on_a_tenth_stays(self):
        self.assertEqual(ceil_to_tenth(Decimal("0.90")), Decimal("0.90"))
        self.assertEqual(ceil_to_tenth(Decimal("3.20")), Decimal("3.20"))
        self.assertEqual(ceil_to_tenth(Decimal("59.00")), Decimal("59.00"))

    def test_zero_and_empty(self):
        self.assertEqual(ceil_to_tenth(Decimal("0.00")), Decimal("0.00"))
        self.assertIsNone(ceil_to_tenth(None))
